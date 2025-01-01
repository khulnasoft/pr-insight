import asyncio
import copy
import re
from functools import partial
from typing import Dict, List, Optional, Tuple

import yaml
from jinja2 import Environment, StrictUndefined

from pr_insight.algo.ai_handlers.base_ai_handler import BaseAiHandler
from pr_insight.algo.ai_handlers.litellm_ai_handler import LiteLLMAIHandler
from pr_insight.algo.pr_processing import (
    get_pr_diff,
    retry_with_fallback_models,
    get_pr_diff_multiple_patchs,
    OUTPUT_BUFFER_TOKENS_HARD_THRESHOLD
)
from pr_insight.algo.token_handler import TokenHandler
from pr_insight.algo.utils import (
    set_custom_labels,
    PRDescriptionHeader,
    load_yaml,
    get_user_labels,
    ModelType,
    show_relevant_configurations,
    get_max_tokens,
    clip_tokens
)
from pr_insight.config_loader import get_settings
from pr_insight.git_providers import get_git_provider, get_git_provider_with_context
from pr_insight.git_providers.git_provider import get_main_pr_language
from pr_insight.log import get_logger
from pr_insight.servers.help import HelpMessage
from pr_insight.tools.ticket_pr_compliance_check import extract_and_cache_pr_tickets


class PRDescription:
    """Generates and manages pull request descriptions using AI."""

    def __init__(
        self,
        pr_url: str,
        args: Optional[List] = None,
        ai_handler: partial[BaseAiHandler,] = LiteLLMAIHandler
    ):
        """
        Initialize PRDescription with necessary attributes for generating PR descriptions.

        Args:
            pr_url: The URL of the pull request
            args: Optional list of arguments
            ai_handler: AI handler class to use, defaults to LiteLLMAIHandler
        """
        self.git_provider = get_git_provider_with_context(pr_url)
        self.main_pr_language = get_main_pr_language(
            self.git_provider.get_languages(),
            self.git_provider.get_files()
        )
        self.pr_id = self.git_provider.get_pr_id()
        self.keys_fix = [
            "filename:",
            "language:",
            "changes_summary:",
            "changes_title:",
            "description:",
            "title:"
        ]

        # Disable semantic files if not supported
        if (get_settings().pr_description.enable_semantic_files_types and 
            not self.git_provider.is_supported("gfm_markdown")):
            get_logger().debug(
                f"Disabling semantic files types for {self.pr_id}, gfm_markdown not supported."
            )
            get_settings().pr_description.enable_semantic_files_types = False

        # Initialize AI handler
        self.ai_handler = ai_handler()
        self.ai_handler.main_pr_language = self.main_pr_language

        # Initialize variables dictionary
        self.vars = {
            "title": self.git_provider.pr.title,
            "branch": self.git_provider.get_pr_branch(),
            "description": self.git_provider.get_pr_description(full=False),
            "language": self.main_pr_language,
            "diff": "",  # Empty diff for initial calculation
            "extra_instructions": get_settings().pr_description.extra_instructions,
            "commit_messages_str": self.git_provider.get_commit_messages(),
            "enable_custom_labels": get_settings().config.enable_custom_labels,
            "custom_labels_class": "",  # Will be filled if necessary in set_custom_labels
            "enable_semantic_files_types": get_settings().pr_description.enable_semantic_files_types,
            "related_tickets": "",
        }

        self.user_description = self.git_provider.get_user_description()

        # Initialize token handler
        self.token_handler = TokenHandler(
            self.git_provider.pr,
            self.vars,
            get_settings().pr_description_prompt.system,
            get_settings().pr_description_prompt.user,
        )

        # Initialize state attributes
        self.patches_diff = None
        self.prediction = None
        self.file_label_dict = None
        self.COLLAPSIBLE_FILE_LIST_THRESHOLD = 8

    async def run(self) -> Optional[str]:
        """
        Run the PR description generation process.
        
        Returns:
            Empty string on success, None on failure
        """
        try:
            get_logger().info(f"Generating a PR description for pr_id: {self.pr_id}")
            
            relevant_configs = {
                'pr_description': dict(get_settings().pr_description),
                'config': dict(get_settings().config)
            }
            get_logger().debug("Relevant configs", artifacts=relevant_configs)

            if (get_settings().config.publish_output and 
                not get_settings().config.get('is_auto_command', False)):
                self.git_provider.publish_comment(
                    "Preparing PR description...",
                    is_temporary=True
                )

            # Extract tickets if they exist
            await extract_and_cache_pr_tickets(self.git_provider, self.vars)

            # Generate prediction
            await retry_with_fallback_models(self._prepare_prediction, ModelType.TURBO)

            if not self.prediction:
                get_logger().warning(f"Empty prediction, PR: {self.pr_id}")
                self.git_provider.remove_initial_comment()
                return None

            self._prepare_data()

            if get_settings().pr_description.enable_semantic_files_types:
                self.file_label_dict = self._prepare_file_labels()

            # Prepare labels and content
            pr_labels = []
            pr_file_changes = []
            if get_settings().pr_description.publish_labels:
                pr_labels = self._prepare_labels()

            if get_settings().pr_description.use_description_markers:
                pr_title, pr_body, changes_walkthrough, pr_file_changes = (
                    self._prepare_pr_answer_with_markers()
                )
            else:
                pr_title, pr_body, changes_walkthrough, pr_file_changes = (
                    self._prepare_pr_answer()
                )
                if (not self.git_provider.is_supported("publish_file_comments") or
                    not get_settings().pr_description.inline_file_summary):
                    pr_body += "\n\n" + changes_walkthrough

            get_logger().debug(
                "PR output",
                artifact={"title": pr_title, "body": pr_body}
            )

            # Add help text
            pr_body = self._add_help_text(pr_body)

            # Add configurations if enabled
            if get_settings().get('config', {}).get('output_relevant_configurations', False):
                pr_body += show_relevant_configurations(relevant_section='pr_description')

            if get_settings().config.publish_output:
                await self._publish_content(pr_title, pr_body, pr_labels)

            return ""

        except Exception as e:
            get_logger().error(f"Error generating PR description {self.pr_id}: {e}")
            return None

    def _add_help_text(self, pr_body: str) -> str:
        """Add help text to PR body if enabled."""
        if self.git_provider.is_supported("gfm_markdown") and get_settings().pr_description.enable_help_text:
            pr_body += (
                "<hr>\n\n"
                "<details> <summary><strong>✨ Describe tool usage guide:</strong></summary><hr> \n\n"
                f"{HelpMessage.get_describe_usage_guide()}\n"
                "</details>\n"
            )
        elif get_settings().pr_description.enable_help_comment:
            pr_body += (
                '\n\n___\n\n'
                '> 💡 **PR-Insight usage**: Comment `/help "your question"` on any pull request '
                'to receive relevant information'
            )
        return pr_body

    async def _publish_content(self, pr_title: str, pr_body: str, pr_labels: List[str]) -> None:
        """Publish the PR content including labels, description and comments."""
        # Publish labels if enabled
        if (get_settings().pr_description.publish_labels and pr_labels and 
            self.git_provider.is_supported("get_labels")):
            await self._publish_labels(pr_labels)

        # Publish description
        if get_settings().pr_description.publish_description_as_comment:
            await self._publish_as_comment(pr_title, pr_body)
        else:
            await self._publish_as_description(pr_title, pr_body)

        self.git_provider.remove_initial_comment()

    async def _publish_labels(self, pr_labels: List[str]) -> None:
        """Publish PR labels if they've changed."""
        original_labels = self.git_provider.get_pr_labels(update=True)
        get_logger().debug("original labels", artifact=original_labels)
        
        user_labels = get_user_labels(original_labels)
        new_labels = pr_labels + user_labels
        get_logger().debug("published labels", artifact=new_labels)
        
        if sorted(new_labels) != sorted(original_labels):
            self.git_provider.publish_labels(new_labels)
        else:
            get_logger().debug("Labels are the same, not updating")

    async def _publish_as_comment(self, pr_title: str, pr_body: str) -> None:
        """Publish the PR content as a comment."""
        full_markdown_description = f"## Title\n\n{pr_title}\n\n___\n{pr_body}"
        
        if get_settings().pr_description.publish_description_as_comment_persistent:
            self.git_provider.publish_persistent_comment(
                full_markdown_description,
                initial_header="## Title",
                update_header=True,
                name="describe",
                final_update_message=False,
            )
        else:
            self.git_provider.publish_comment(full_markdown_description)

    async def _publish_as_description(self, pr_title: str, pr_body: str) -> None:
        """Publish the PR content as the PR description."""
        self.git_provider.publish_description(pr_title, pr_body)

        if get_settings().pr_description.final_update_message:
            latest_commit_url = self.git_provider.get_latest_commit_url()
            if latest_commit_url:
                pr_url = self.git_provider.get_pr_url()
                update_comment = (
                    f"**[PR Description]({pr_url})** updated to latest commit "
                    f"({latest_commit_url})"
                )
                self.git_provider.publish_comment(update_comment)

    async def _prepare_prediction(self, model: str) -> None:
        """
        Prepare the AI prediction for the PR description.
        
        Args:
            model: The model name to use for prediction
        """
        if (get_settings().pr_description.use_description_markers and 
            'pr_insight:' not in self.user_description):
            get_logger().info(
                "Markers were enabled, but user description does not contain markers. "
                "skipping AI prediction"
            )
            return None

        large_pr_handling = (
            get_settings().pr_description.enable_large_pr_handling and 
            "pr_description_only_files_prompts" in get_settings()
        )

        output = get_pr_diff(
            self.git_provider,
            self.token_handler,
            model,
            large_pr_handling=large_pr_handling,
            return_remaining_files=True
        )

        if isinstance(output, tuple):
            patches_diff, remaining_files_list = output
        else:
            patches_diff = output
            remaining_files_list = []

        if not large_pr_handling or patches_diff:
            await self._handle_standard_prediction(
                model, patches_diff, remaining_files_list
            )
        else:
            await self._handle_large_pr_prediction(model)

    async def _handle_standard_prediction(
        self,
        model: str,
        patches_diff: str,
        remaining_files_list: List[str]
    ) -> None:
        """Handle prediction for standard-sized PRs."""
        self.patches_diff = patches_diff
        if patches_diff:
            get_logger().debug("PR diff", artifact=self.patches_diff)
            self.prediction = await self._get_prediction(
                model,
                patches_diff,
                prompt="pr_description_prompt"
            )

            if (remaining_files_list and 'pr_files' in self.prediction and
                'label:' in self.prediction and
                get_settings().pr_description.mention_extra_files):
                get_logger().debug(
                    f"Extending additional files, {len(remaining_files_list)} files"
                )
                self.prediction = await self.extend_additional_files(
                    remaining_files_list
                )
        else:
            get_logger().error(f"Error getting PR diff {self.pr_id}")
            self.prediction = None

    async def _handle_large_pr_prediction(self, model: str) -> None:
        """Handle prediction for large PRs using multiple patches."""
        get_logger().debug('large_pr_handling for describe')
        
        token_handler_only_files_prompt = TokenHandler(
            self.git_provider.pr,
            self.vars,
            get_settings().pr_description_only_files_prompts.system,
            get_settings().pr_description_only_files_prompts.user,
        )

        (patches_compressed_list, total_tokens_list, deleted_files_list,
         remaining_files_list, file_dict, files_in_patches_list) = (
            get_pr_diff_multiple_patchs(
                self.git_provider,
                token_handler_only_files_prompt,
                model
            )
        )

        # Get predictions for each patch
        results = await self._get_patch_predictions(
            model, patches_compressed_list
        )

        # Process results
        file_description_str_list = self._process_patch_results(results)

        # Generate files walkthrough
        await self._generate_files_walkthrough(
            model,
            file_description_str_list,
            remaining_files_list,
            deleted_files_list
        )

    async def _get_patch_predictions(
        self,
        model: str,
        patches_compressed_list: List[List[str]]
    ) -> List[str]:
        """Get predictions for each patch in parallel or sequentially."""
        if not get_settings().pr_description.async_ai_calls:
            # Synchronous calls
            results = []
            for i, patches in enumerate(patches_compressed_list):
                patches_diff = "\n".join(patches)
                get_logger().debug(f"PR diff number {i + 1} for describe files")
                prediction_files = await self._get_prediction(
                    model,
                    patches_diff,
                    prompt="pr_description_only_files_prompts"
                )
                results.append(prediction_files)
        else:
            # Asynchronous calls
            tasks = []
            for i, patches in enumerate(patches_compressed_list):
                if patches:
                    patches_diff = "\n".join(patches)
                    get_logger().debug(f"PR diff number {i + 1} for describe files")
                    task = asyncio.create_task(
                        self._get_prediction(
                            model,
                            patches_diff,
                            prompt="pr_description_only_files_prompts"
                        )
                    )
                    tasks.append(task)
            results = await asyncio.gather(*tasks)

        return results

    def _process_patch_results(self, results: List[str]) -> List[str]:
        """Process prediction results from patches."""
        file_description_str_list = []
        for i, result in enumerate(results):
            prediction_files = result.strip().removeprefix('```yaml').strip('`').strip()
            if load_yaml(prediction_files, keys_fix_yaml=self.keys_fix) and prediction_files.startswith('pr_files'):
                prediction_files = prediction_files.removeprefix('pr_files:').strip()
                file_description_str_list.append(prediction_files)
            else:
                get_logger().debug(
                    f"failed to generate predictions in iteration {i + 1} for describe files"
                )
        return file_description_str_list

    async def _generate_files_walkthrough(
        self,
        model: str,
        file_description_str_list: List[str],
        remaining_files_list: List[str],
        deleted_files_list: List[str]
    ) -> None:
        """Generate walkthrough of files with proper token handling."""
        token_handler_only_description_prompt = TokenHandler(
            self.git_provider.pr,
            self.vars,
            get_settings().pr_description_only_description_prompts.system,
            get_settings().pr_description_only_description_prompts.user
        )

        files_walkthrough = "\n".join(file_description_str_list)
        files_walkthrough_prompt = self._prepare_files_walkthrough_prompt(
            files_walkthrough,
            remaining_files_list,
            deleted_files_list
        )

        # Handle token limits
        tokens_files_walkthrough = len(
            token_handler_only_description_prompt.encoder.encode(
                files_walkthrough_prompt
            )
        )
        total_tokens = (
            token_handler_only_description_prompt.prompt_tokens +
            tokens_files_walkthrough
        )
        max_tokens_model = get_max_tokens(model)

        if total_tokens > max_tokens_model - OUTPUT_BUFFER_TOKENS_HARD_THRESHOLD:
            files_walkthrough_prompt = clip_tokens(
                files_walkthrough_prompt,
                max_tokens_model - OUTPUT_BUFFER_TOKENS_HARD_THRESHOLD -
                token_handler_only_description_prompt.prompt_tokens,
                num_input_tokens=tokens_files_walkthrough
            )

        # PR header inference
        get_logger().debug(
            "PR diff only description",
            artifact=files_walkthrough_prompt
        )
        prediction_headers = await self._get_prediction(
            model,
            patches_diff=files_walkthrough_prompt,
            prompt="pr_description_only_description_prompts"
        )
        prediction_headers = (
            prediction_headers.strip()
            .removeprefix('```yaml')
            .strip('`')
            .strip()
        )

        # Add extra files to final prediction
        files_walkthrough = self._add_extra_files_to_walkthrough(
            files_walkthrough,
            remaining_files_list
        )

        # Final processing
        self.prediction = prediction_headers + "\n" + "pr_files:\n" + files_walkthrough
        if not load_yaml(self.prediction, keys_fix_yaml=self.keys_fix):
            get_logger().error(
                f"Error getting valid YAML in large PR handling for describe {self.pr_id}"
            )
            if load_yaml(prediction_headers, keys_fix_yaml=self.keys_fix):
                get_logger().debug(f"Using only headers for describe {self.pr_id}")
                self.prediction = prediction_headers

    def _prepare_files_walkthrough_prompt(
        self,
        files_walkthrough: str,
        remaining_files_list: List[str],
        deleted_files_list: List[str]
    ) -> str:
        """Prepare the files walkthrough prompt with remaining and deleted files."""
        MAX_EXTRA_FILES_TO_PROMPT = 50
        files_walkthrough_prompt = copy.deepcopy(files_walkthrough)

        if remaining_files_list:
            files_walkthrough_prompt += "\n\nNo more token budget. Additional unprocessed files:"
            for i, file in enumerate(remaining_files_list):
                files_walkthrough_prompt += f"\n- {file}"
                if i >= MAX_EXTRA_FILES_TO_PROMPT:
                    files_walkthrough_prompt += (
                        f"\n... and {len(remaining_files_list) - MAX_EXTRA_FILES_TO_PROMPT} more"
                    )
                    break

        if deleted_files_list:
            files_walkthrough_prompt += "\n\nAdditional deleted files:"
            for i, file in enumerate(deleted_files_list):
                files_walkthrough_prompt += f"\n- {file}"
                if i >= MAX_EXTRA_FILES_TO_PROMPT:
                    files_walkthrough_prompt += (
                        f"\n... and {len(deleted_files_list) - MAX_EXTRA_FILES_TO_PROMPT} more"
                    )
                    break

        return files_walkthrough_prompt

    def _add_extra_files_to_walkthrough(
        self,
        files_walkthrough: str,
        remaining_files_list: List[str]
    ) -> str:
        """Add extra files to the walkthrough with proper formatting."""
        MAX_EXTRA_FILES_TO_OUTPUT = 100
        
        if get_settings().pr_description.mention_extra_files:
            for i, file in enumerate(remaining_files_list):
                extra_file_yaml = f"""\
- filename: |
    {file}
  changes_summary: |
    ...
  changes_title: |
    ...
  label: |
    additional files (token-limit)
"""
                files_walkthrough = files_walkthrough.strip() + "\n" + extra_file_yaml.strip()
                if i >= MAX_EXTRA_FILES_TO_OUTPUT:
                    files_walkthrough += f"""\
- filename: |
    Additional {len(remaining_files_list) - MAX_EXTRA_FILES_TO_OUTPUT} files not shown
  changes_summary: |
    ...
  changes_title: |
    ...
  label: |
    additional files (token-limit)
"""
                    break

        return files_walkthrough

    async def extend_additional_files(self, remaining_files_list: List[str]) -> str:
        """Extend the prediction with additional files."""
        try:
            original_prediction_dict = load_yaml(
                self.prediction,
                keys_fix_yaml=self.keys_fix
            )
            
            prediction_extra = "pr_files:"
            for file in remaining_files_list:
                extra_file_yaml = f"""\
- filename: |
    {file}
  changes_summary: |
    ...
  changes_title: |
    ...
  label: |
    additional files (token-limit)
"""
                prediction_extra = prediction_extra + "\n" + extra_file_yaml.strip()
            
            prediction_extra_dict = load_yaml(
                prediction_extra,
                keys_fix_yaml=self.keys_fix
            )
            
            # Merge the dictionaries
            if isinstance(original_prediction_dict, dict) and isinstance(prediction_extra_dict, dict):
                original_prediction_dict["pr_files"].extend(prediction_extra_dict["pr_files"])
                new_yaml = yaml.dump(original_prediction_dict)
                if load_yaml(new_yaml, keys_fix_yaml=self.keys_fix):
                    return new_yaml
                    
            return self.prediction
            
        except Exception as e:
            get_logger().error(f"Error extending additional files {self.pr_id}: {e}")
            return self.prediction

    async def _get_prediction(
        self,
        model: str,
        patches_diff: str,
        prompt: str = "pr_description_prompt"
    ) -> str:
        """
        Get an AI prediction for the PR description.

        Args:
            model: The model to use
            patches_diff: The diff patches to analyze
            prompt: The prompt template to use

        Returns:
            The prediction text
        """
        variables = copy.deepcopy(self.vars)
        variables["diff"] = patches_diff

        environment = Environment(undefined=StrictUndefined)
        set_custom_labels(variables, self.git_provider)
        self.variables = variables

        system_prompt = environment.from_string(
            get_settings().get(prompt, {}).get("system", "")
        ).render(self.variables)
        
        user_prompt = environment.from_string(
            get_settings().get(prompt, {}).get("user", "")
        ).render(self.variables)

        response, finish_reason = await self.ai_handler.chat_completion(
            model=model,
            temperature=get_settings().config.temperature,
            system=system_prompt,
            user=user_prompt
        )

        return response

    def _prepare_data(self) -> None:
        """Prepare the prediction data for use."""
        self.data = load_yaml(self.prediction.strip(), keys_fix_yaml=self.keys_fix)

        if get_settings().pr_description.add_original_user_description and self.user_description:
            self.data["User Description"] = self.user_description

        # Re-order keys for consistent output
        ordered_keys = [
            'User Description',
            'title',
            'type',
            'labels',
            'description',
            'pr_files'
        ]
        
        for key in ordered_keys:
            if key in self.data:
                self.data[key] = self.data.pop(key)

    def _prepare_labels(self) -> List[str]:
        """Prepare labels from the prediction data."""
        pr_types = []

        # Extract labels from prediction
        if 'labels' in self.data:
            if isinstance(self.data['labels'], list):
                pr_types = self.data['labels']
            elif isinstance(self.data['labels'], str):
                pr_types = self.data['labels'].split(',')
        elif 'type' in self.data:
            if isinstance(self.data['type'], list):
                pr_types = self.data['type']
            elif isinstance(self.data['type'], str):
                pr_types = self.data['type'].split(',')

        pr_types = [label.strip() for label in pr_types]

        # Convert lowercase labels to original case
        try:
            if "labels_minimal_to_labels_dict" in self.variables:
                labels_dict: Dict[str, str] = self.variables["labels_minimal_to_labels_dict"]
                pr_types = [
                    labels_dict.get(label, label)
                    for label in pr_types
                ]
        except Exception as e:
            get_logger().error(
                f"Error converting labels to original case {self.pr_id}: {e}"
            )

        return pr_types

    def _prepare_file_labels(self) -> Dict[str, List[Tuple[str, str, str]]]:
        """
        Prepare file labels from the prediction data.
        
        Returns:
            Dictionary mapping labels to lists of (filename, title, summary) tuples
        """
        file_label_dict: Dict[str, List[Tuple[str, str, str]]] = {}
        
        if (not self.data or not isinstance(self.data, dict) or
            'pr_files' not in self.data or not self.data['pr_files']):
            return file_label_dict

        required_fields = ['changes_summary', 'changes_title', 'filename', 'label']
            
        for file in self.data['pr_files']:
            try:
                if not all(field in file for field in required_fields):
                    get_logger().warning(
                        f"Missing required fields in file label dict {self.pr_id}, skipping file",
                        artifact={"file": file}
                    )
                    continue
                    
                filename = file['filename'].replace("'", "`").replace('"', '`')
                changes_summary = file['changes_summary']
                changes_title = file['changes_title'].strip()
                label = file.get('label').strip().lower()
                
                if label not in file_label_dict:
                    file_label_dict[label] = []
                    
                file_label_dict[label].append(
                    (filename, changes_title, changes_summary)
                )
                
            except Exception as e:
                get_logger().error(
                    f"Error preparing file label dict {self.pr_id}: {e}"
                )
                
        return file_label_dict

    def _prepare_pr_answer_with_markers(self) -> Tuple[str, str, str, List[dict]]:
        """
        Prepare PR description using markers in the user description.
        
        Returns:
            Tuple of (title, body, changes walkthrough, file changes)
        """
        get_logger().info(f"Using description marker replacements {self.pr_id}")
        
        title = self.vars["title"]
        body = self.user_description
        
        if get_settings().pr_description.include_generated_by_header:
            ai_header = f"### 🤖 Generated by PR Insight at {self.git_provider.last_commit_id.sha}\n\n"
        else:
            ai_header = ""

        # Replace type marker
        ai_type = self.data.get('type')
        if ai_type and not re.search(r'<!--\s*pr_insight:type\s*-->', body):
            pr_type = f"{ai_header}{ai_type}"
            body = body.replace('pr_insight:type', pr_type)

        # Replace summary marker
        ai_summary = self.data.get('description')
        if ai_summary and not re.search(r'<!--\s*pr_insight:summary\s*-->', body):
            summary = f"{ai_header}{ai_summary}"
            body = body.replace('pr_insight:summary', summary)

        # Replace walkthrough marker
        ai_walkthrough = self.data.get('pr_files')
        walkthrough_gfm = ""
        pr_file_changes = []
        
        if ai_walkthrough and not re.search(r'<!--\s*pr_insight:walkthrough\s*-->', body):
            try:
                walkthrough_gfm, pr_file_changes = self.process_pr_files_prediction(
                    walkthrough_gfm,
                    self.file_label_dict
                )
                body = body.replace('pr_insight:walkthrough', walkthrough_gfm)
            except Exception as e:
                get_logger().error(f"Failing to process walkthrough {self.pr_id}: {e}")
                body = body.replace('pr_insight:walkthrough', "")

        return title, body, walkthrough_gfm, pr_file_changes

    def _prepare_pr_answer(self) -> Tuple[str, str, str, List[dict]]:
        """
        Prepare PR description without markers.
        
        Returns:
            Tuple of (title, body, changes walkthrough, file changes)
        """
        markdown_text = ""
        
        # Don't display labels if they'll be published separately
        if 'labels' in self.data and self.git_provider.is_supported("get_labels"):
            self.data.pop('labels')
            
        if not get_settings().pr_description.enable_pr_type:
            self.data.pop('type')
        for key, value in self.data.items():
            markdown_text += f"## **{key}**\n\n"
            markdown_text += f"{value}\n\n"

        # Remove the 'PR Title' key from the dictionary
        ai_title = self.data.pop('title', self.vars["title"])
        if (not get_settings().pr_description.generate_ai_title):
            # Assign the original PR title to the 'title' variable
            title = self.vars["title"]
        else:
            # Assign the value of the 'PR Title' key to 'title' variable
            title = ai_title

        # Iterate over the remaining dictionary items and append the key and value to 'pr_body' in a markdown format,
        # except for the items containing the word 'walkthrough'
        pr_body, changes_walkthrough = "", ""
        pr_file_changes = []
        for idx, (key, value) in enumerate(self.data.items()):
            if key == 'pr_files':
                value = self.file_label_dict
            else:
                key_publish = key.rstrip(':').replace("_", " ").capitalize()
                if key_publish == "Type":
                    key_publish = "PR Type"
                # elif key_publish == "Description":
                #     key_publish = "PR Description"
                pr_body += f"### **{key_publish}**\n"
            if 'walkthrough' in key.lower():
                if self.git_provider.is_supported("gfm_markdown"):
                    pr_body += "<details> <summary>files:</summary>\n\n"
                for file in value:
                    filename = file['filename'].replace("'", "`")
                    description = file['changes_in_file']
                    pr_body += f'- `{filename}`: {description}\n'
                if self.git_provider.is_supported("gfm_markdown"):
                    pr_body += "</details>\n"
            elif 'pr_files' in key.lower() and get_settings().pr_description.enable_semantic_files_types:
                changes_walkthrough, pr_file_changes = self.process_pr_files_prediction(changes_walkthrough, value)
                changes_walkthrough = f"{PRDescriptionHeader.CHANGES_WALKTHROUGH.value}\n{changes_walkthrough}"
            else:
                # if the value is a list, join its items by comma
                if isinstance(value, list):
                    value = ', '.join(v.rstrip() for v in value)
                pr_body += f"{value}\n"
            if idx < len(self.data) - 1:
                pr_body += "\n\n___\n\n"

        return title, pr_body, changes_walkthrough, pr_file_changes,

    def _prepare_file_labels(self):
        file_label_dict = {}
        if (not self.data or not isinstance(self.data, dict) or
                'pr_files' not in self.data or not self.data['pr_files']):
            return file_label_dict
        for file in self.data['pr_files']:
            try:
                required_fields = ['changes_summary', 'changes_title', 'filename', 'label']
                if not all(field in file for field in required_fields):
                    # can happen for example if a YAML generation was interrupted in the middle (no more tokens)
                    get_logger().warning(f"Missing required fields in file label dict {self.pr_id}, skipping file",
                                         artifact={"file": file})
                    continue
                filename = file['filename'].replace("'", "`").replace('"', '`')
                changes_summary = file['changes_summary']
                changes_title = file['changes_title'].strip()
                label = file.get('label').strip().lower()
                if label not in file_label_dict:
                    file_label_dict[label] = []
                file_label_dict[label].append((filename, changes_title, changes_summary))
            except Exception as e:
                get_logger().error(f"Error preparing file label dict {self.pr_id}: {e}")
                pass
        return file_label_dict

    def process_pr_files_prediction(self, pr_body, value):
        pr_comments = []
        # logic for using collapsible file list
        use_collapsible_file_list = get_settings().pr_description.collapsible_file_list
        num_files = 0
        if value:
            for semantic_label in value.keys():
                num_files += len(value[semantic_label])
        if use_collapsible_file_list == "adaptive":
            use_collapsible_file_list = num_files > self.COLLAPSIBLE_FILE_LIST_THRESHOLD

        if not self.git_provider.is_supported("gfm_markdown"):
            return pr_body, pr_comments
        try:
            pr_body += "<table>"
            header = f"Relevant files"
            delta = 75
            # header += "&nbsp; " * delta
            pr_body += f"""<thead><tr><th></th><th align="left">{header}</th></tr></thead>"""
            pr_body += """<tbody>"""
            for semantic_label in value.keys():
                s_label = semantic_label.strip("'").strip('"')
                pr_body += f"""<tr><td><strong>{s_label.capitalize()}</strong></td>"""
                list_tuples = value[semantic_label]

                if use_collapsible_file_list:
                    pr_body += f"""<td><details><summary>{len(list_tuples)} files</summary><table>"""
                else:
                    pr_body += f"""<td><table>"""
                for filename, file_changes_title, file_change_description in list_tuples:
                    filename = filename.replace("'", "`").rstrip()
                    filename_publish = filename.split("/")[-1]

                    file_changes_title_code = f"<code>{file_changes_title}</code>"
                    file_changes_title_code_br = insert_br_after_x_chars(file_changes_title_code, x=(delta - 5)).strip()
                    if len(file_changes_title_code_br) < (delta - 5):
                        file_changes_title_code_br += "&nbsp; " * ((delta - 5) - len(file_changes_title_code_br))
                    filename_publish = f"<strong>{filename_publish}</strong><dd>{file_changes_title_code_br}</dd>"
                    diff_plus_minus = ""
                    delta_nbsp = ""
                    diff_files = self.git_provider.get_diff_files()
                    for f in diff_files:
                        if f.filename.lower().strip('/') == filename.lower().strip('/'):
                            num_plus_lines = f.num_plus_lines
                            num_minus_lines = f.num_minus_lines
                            diff_plus_minus += f"+{num_plus_lines}/-{num_minus_lines}"
                            delta_nbsp = "&nbsp; " * max(0, (8 - len(diff_plus_minus)))
                            break

                    # try to add line numbers link to code suggestions
                    link = ""
                    if hasattr(self.git_provider, 'get_line_link'):
                        filename = filename.strip()
                        link = self.git_provider.get_line_link(filename, relevant_line_start=-1)

                    file_change_description_br = insert_br_after_x_chars(file_change_description, x=(delta - 5))
                    pr_body += f"""
<tr>
  <td>
    <details>
      <summary>{filename_publish}</summary>
<hr>

{filename}

{file_change_description_br}


</details>


  </td>
  <td><a href="{link}">{diff_plus_minus}</a>{delta_nbsp}</td>

</tr>                    
"""
                if use_collapsible_file_list:
                    pr_body += """</table></details></td></tr>"""
                else:
                    pr_body += """</table></td></tr>"""
            pr_body += """</tr></tbody></table>"""

        except Exception as e:
            get_logger().error(f"Error processing pr files to markdown {self.pr_id}: {e}")
            pass
        return pr_body, pr_comments


def count_chars_without_html(string):
    if '<' not in string:
        return len(string)
    no_html_string = re.sub('<[^>]+>', '', string)
    return len(no_html_string)


def insert_br_after_x_chars(text, x=70):
    """
    Insert <br> into a string after a word that increases its length above x characters.
    Use proper HTML tags for code and new lines.
    """
    if count_chars_without_html(text) < x:
        return text

    # replace odd instances of ` with <code> and even instances of ` with </code>
    text = replace_code_tags(text)

    # convert list items to <li>
    if text.startswith("- ") or text.startswith("* "):
        text = "<li>" + text[2:]
    text = text.replace("\n- ", '<br><li> ').replace("\n - ", '<br><li> ')
    text = text.replace("\n* ", '<br><li> ').replace("\n * ", '<br><li> ')

    # convert new lines to <br>
    text = text.replace("\n", '<br>')

    # split text into lines
    lines = text.split('<br>')
    words = []
    for i, line in enumerate(lines):
        words += line.split(' ')
        if i < len(lines) - 1:
            words[-1] += "<br>"

    new_text = []
    is_inside_code = False
    current_length = 0
    for word in words:
        is_saved_word = False
        if word == "<code>" or word == "</code>" or word == "<li>" or word == "<br>":
            is_saved_word = True

        len_word = count_chars_without_html(word)
        if not is_saved_word and (current_length + len_word > x):
            if is_inside_code:
                new_text.append("</code><br><code>")
            else:
                new_text.append("<br>")
            current_length = 0  # Reset counter
        new_text.append(word + " ")

        if not is_saved_word:
            current_length += len_word + 1  # Add 1 for the space

        if word == "<li>" or word == "<br>":
            current_length = 0

        if "<code>" in word:
            is_inside_code = True
        if "</code>" in word:
            is_inside_code = False
    return ''.join(new_text).strip()


def replace_code_tags(text):
    """
    Replace odd instances of ` with <code> and even instances of ` with </code>
    """
    parts = text.split('`')
    for i in range(1, len(parts), 2):
        parts[i] = '<code>' + parts[i] + '</code>'
    return ''.join(parts)
