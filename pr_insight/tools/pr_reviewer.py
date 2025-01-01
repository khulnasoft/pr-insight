import copy
import datetime
import traceback
from collections import OrderedDict
from functools import partial
from typing import List, Tuple, Optional, Dict, Any
from jinja2 import Environment, StrictUndefined
from pr_insight.algo.ai_handlers.base_ai_handler import BaseAiHandler
from pr_insight.algo.ai_handlers.litellm_ai_handler import LiteLLMAIHandler
from pr_insight.algo.pr_processing import get_pr_diff, retry_with_fallback_models, add_ai_metadata_to_diff_files
from pr_insight.algo.token_handler import TokenHandler
from pr_insight.algo.utils import github_action_output, load_yaml, ModelType, \
    show_relevant_configurations, convert_to_markdown_v2, PRReviewHeader
from pr_insight.config_loader import get_settings
from pr_insight.git_providers import get_git_provider, get_git_provider_with_context
from pr_insight.git_providers.git_provider import IncrementalPR, get_main_pr_language
from pr_insight.log import get_logger
from pr_insight.servers.help import HelpMessage
from pr_insight.tools.ticket_pr_compliance_check import extract_tickets, extract_and_cache_pr_tickets


class PRReviewer:
    """
    The PRReviewer class is responsible for reviewing a pull request and generating feedback using an AI model.
    It handles:
    - Initializing the review with PR metadata and configuration
    - Running the AI model to analyze the PR
    - Formatting and publishing the review results
    - Managing incremental reviews and auto-approval flows
    """

    def __init__(self, pr_url: str, is_answer: bool = False, is_auto: bool = False, args: Optional[List[str]] = None,
                 ai_handler: partial[BaseAiHandler,] = LiteLLMAIHandler):
        """
        Initialize the PRReviewer with the necessary attributes and objects.

        Args:
            pr_url: The URL of the pull request to review
            is_answer: Whether this is an answer to a previous review question
            is_auto: Whether this is an automated review
            args: Additional command line arguments
            ai_handler: The AI handler class to use for generating reviews
        """
        self.git_provider = get_git_provider_with_context(pr_url)
        self.args = args
        self.incremental = self._parse_incremental(args)
        if self.incremental and self.incremental.is_incremental:
            self.git_provider.get_incremental_commits(self.incremental)

        self.main_language = get_main_pr_language(
            self.git_provider.get_languages(), 
            self.git_provider.get_files()
        )
        self.pr_url = pr_url
        self.is_answer = is_answer
        self.is_auto = is_auto

        if self.is_answer and not self.git_provider.is_supported("get_issue_comments"):
            raise Exception(f"Answer mode is not supported for {get_settings().config.git_provider}")
            
        self.ai_handler = ai_handler()
        self.ai_handler.main_pr_language = self.main_language
        self.patches_diff: Optional[str] = None
        self.prediction: Optional[str] = None

        # Get PR description and metadata
        answer_str, question_str = self._get_user_answers()
        self.pr_description, self.pr_description_files = (
            self.git_provider.get_pr_description(split_changes_walkthrough=True)
        )

        # Handle AI metadata if enabled
        self._handle_ai_metadata()

        # Initialize template variables
        self.vars = self._init_template_vars(answer_str, question_str)

        # Initialize token handler
        self.token_handler = TokenHandler(
            self.git_provider.pr,
            self.vars,
            get_settings().pr_review_prompt.system,
            get_settings().pr_review_prompt.user
        )

    def _parse_incremental(self, args: Optional[List[str]]) -> IncrementalPR:
        """Parse incremental review flag from arguments"""
        is_incremental = bool(args and args[0] == "-i")
        return IncrementalPR(is_incremental)

    def _handle_ai_metadata(self) -> None:
        """Handle AI metadata configuration and processing"""
        if (self.pr_description_files and 
            get_settings().get("config.is_auto_command", False) and
            get_settings().get("config.enable_ai_metadata", False)):
            
            add_ai_metadata_to_diff_files(self.git_provider, self.pr_description_files)
            get_logger().debug("AI metadata added to this command")
        else:
            get_settings().set("config.enable_ai_metadata", False) 
            get_logger().debug("AI metadata is disabled for this command")

    def _init_template_vars(self, answer_str: str, question_str: str) -> Dict[str, Any]:
        """Initialize template variables for the review"""
        return {
            "title": self.git_provider.pr.title,
            "branch": self.git_provider.get_pr_branch(),
            "description": self.pr_description,
            "language": self.main_language,
            "diff": "",  # empty diff for initial calculation
            "num_pr_files": self.git_provider.get_num_of_files(),
            "require_score": get_settings().pr_reviewer.require_score_review,
            "require_tests": get_settings().pr_reviewer.require_tests_review,
            "require_estimate_effort_to_review": get_settings().pr_reviewer.require_estimate_effort_to_review,
            'require_can_be_split_review': get_settings().pr_reviewer.require_can_be_split_review,
            'require_security_review': get_settings().pr_reviewer.require_security_review,
            'num_code_suggestions': get_settings().pr_reviewer.num_code_suggestions,
            'question_str': question_str,
            'answer_str': answer_str,
            "extra_instructions": get_settings().pr_reviewer.extra_instructions,
            "commit_messages_str": self.git_provider.get_commit_messages(),
            "custom_labels": "",
            "enable_custom_labels": get_settings().config.enable_custom_labels,
            "is_ai_metadata": get_settings().get("config.enable_ai_metadata", False),
            "related_tickets": get_settings().get('related_tickets', []),
        }

    async def run(self) -> None:
        """
        Run the PR review process. This includes:
        - Validating the PR can be reviewed
        - Running the AI model analysis
        - Publishing the review results
        """
        try:
            if not self._validate_can_review():
                return

            if self.args and self.args[0] == 'auto_approve':
                get_logger().info(f'Auto approve flow PR: {self.pr_url} ...')
                self.auto_approve_logic()
                return

            get_logger().info(f'Reviewing PR: {self.pr_url} ...')
            self._log_config()

            # Extract tickets if they exist
            await extract_and_cache_pr_tickets(self.git_provider, self.vars)

            if self._should_skip_incremental():
                return

            if get_settings().config.publish_output and not get_settings().config.get('is_auto_command', False):
                self.git_provider.publish_comment("Preparing review...", is_temporary=True)

            # Generate and publish review
            await retry_with_fallback_models(self._prepare_prediction)
            if not self.prediction:
                self.git_provider.remove_initial_comment()
                return

            pr_review = self._prepare_pr_review()
            get_logger().debug("PR output", artifact=pr_review)

            self._publish_review(pr_review)

            if get_settings().pr_reviewer.inline_code_comments:
                self._publish_inline_code_comments()

        except Exception as e:
            get_logger().error(f"Failed to review PR: {e}")
            get_logger().debug(traceback.format_exc())

    def _validate_can_review(self) -> bool:
        """Validate that the PR can be reviewed"""
        if not self.git_provider.get_files():
            get_logger().info(f"PR has no files: {self.pr_url}, skipping review")
            return False

        if self.incremental.is_incremental and not self._can_run_incremental_review():
            return False

        return True

    def _log_config(self) -> None:
        """Log relevant configuration settings"""
        relevant_configs = {
            'pr_reviewer': dict(get_settings().pr_reviewer),
            'config': dict(get_settings().config)
        }
        get_logger().debug("Relevant configs", artifacts=relevant_configs)

    def _should_skip_incremental(self) -> bool:
        """Determine if incremental review should be skipped"""
        if (self.incremental.is_incremental and 
            hasattr(self.git_provider, "unreviewed_files_set") and 
            not self.git_provider.unreviewed_files_set):
            
            get_logger().info(f"Incremental review is enabled for {self.pr_url} but there are no new files")
            previous_review_url = ""
            if hasattr(self.git_provider, "previous_review"):
                previous_review_url = self.git_provider.previous_review.html_url
                
            if get_settings().config.publish_output:
                self.git_provider.publish_comment(
                    f"Incremental Review Skipped\n"
                    f"No files were changed since the [previous PR Review]({previous_review_url})"
                )
            return True
        return False

    def _publish_review(self, pr_review: str) -> None:
        """Publish the review results"""
        if get_settings().config.publish_output:
            if get_settings().pr_reviewer.persistent_comment and not self.incremental.is_incremental:
                final_update_message = get_settings().pr_reviewer.final_update_message
                self.git_provider.publish_persistent_comment(
                    pr_review,
                    initial_header=f"{PRReviewHeader.REGULAR.value} 🔍",
                    update_header=True,
                    final_update_message=final_update_message
                )
            else:
                self.git_provider.publish_comment(pr_review)

            self.git_provider.remove_initial_comment()

    async def _prepare_prediction(self, model: str) -> None:
        """Prepare the AI model prediction"""
        self.patches_diff = get_pr_diff(
            self.git_provider,
            self.token_handler,
            model,
            add_line_numbers_to_hunks=True,
            disable_extra_lines=False
        )

        if self.patches_diff:
            get_logger().debug("PR diff", diff=self.patches_diff)
            self.prediction = await self._get_prediction(model)
        else:
            get_logger().warning(f"Empty diff for PR: {self.pr_url}")
            self.prediction = None

    async def _get_prediction(self, model: str) -> str:
        """Generate an AI prediction for the PR review"""
        variables = copy.deepcopy(self.vars)
        variables["diff"] = self.patches_diff

        environment = Environment(undefined=StrictUndefined)
        system_prompt = environment.from_string(get_settings().pr_review_prompt.system).render(variables)
        user_prompt = environment.from_string(get_settings().pr_review_prompt.user).render(variables)

        response, finish_reason = await self.ai_handler.chat_completion(
            model=model,
            temperature=get_settings().config.temperature,
            system=system_prompt,
            user=user_prompt
        )

        return response

    def _prepare_pr_review(self) -> str:
        """Process the AI prediction and generate formatted review text"""
        first_key = 'review'
        last_key = 'security_concerns'
        data = load_yaml(
            self.prediction.strip(),
            keys_fix_yaml=[
                "ticket_compliance_check", 
                "estimated_effort_to_review_[1-5]:", 
                "security_concerns:", 
                "key_issues_to_review:",
                "relevant_file:", 
                "relevant_line:", 
                "suggestion:"
            ],
            first_key=first_key, 
            last_key=last_key
        )
        github_action_output(data, 'review')

        # Reorder review sections
        if 'key_issues_to_review' in data['review']:
            key_issues = data['review'].pop('key_issues_to_review')
            data['review']['key_issues_to_review'] = key_issues

        self._process_code_feedback(data)

        # Add incremental review section if needed
        incremental_text = None
        if self.incremental.is_incremental:
            last_commit_url = (
                f"{self.git_provider.get_pr_url()}/commits/"
                f"{self.git_provider.incremental.first_new_commit_sha}"
            )
            incremental_text = f"Starting from commit {last_commit_url}"

        # Convert to markdown
        markdown_text = convert_to_markdown_v2(
            data,
            self.git_provider.is_supported("gfm_markdown"),
            incremental_text,
            git_provider=self.git_provider
        )

        # Add help text if supported
        if (self.git_provider.is_supported("gfm_markdown") and 
            get_settings().pr_reviewer.enable_help_text):
            markdown_text += (
                "<hr>\n\n<details> <summary><strong>💡 Tool usage guide:</strong></summary><hr> \n\n"
                f"{HelpMessage.get_review_usage_guide()}\n</details>\n"
            )

        # Add configurations if enabled
        if get_settings().get('config', {}).get('output_relevant_configurations', False):
            markdown_text += show_relevant_configurations(relevant_section='pr_reviewer')

        # Set review labels
        self.set_review_labels(data)

        return markdown_text or ""

    def _process_code_feedback(self, data: Dict[str, Any]) -> None:
        """Process code feedback section of the review"""
        if 'code_feedback' not in data:
            return

        code_feedback = data['code_feedback']

        # Remove code feedback if using inline comments
        if get_settings().pr_reviewer.inline_code_comments:
            del data['code_feedback']
            return

        # Format code suggestions
        for suggestion in code_feedback:
            if ('relevant_file' in suggestion and 
                not suggestion['relevant_file'].startswith('``')):
                suggestion['relevant_file'] = f"``{suggestion['relevant_file']}``"

            if 'relevant_line' not in suggestion:
                suggestion['relevant_line'] = ''

            relevant_line = suggestion['relevant_line'].split('\n')[0]
            suggestion['relevant_line'] = relevant_line.lstrip('+').strip()

            # Add line number links if supported
            if hasattr(self.git_provider, 'generate_link_to_relevant_line_number'):
                link = self.git_provider.generate_link_to_relevant_line_number(suggestion)
                if link:
                    suggestion['relevant_line'] = f"[{suggestion['relevant_line']}]({link})"

    def _publish_inline_code_comments(self) -> None:
        """Publish inline comments for code suggestions"""
        if get_settings().pr_reviewer.num_code_suggestions == 0:
            return

        first_key = 'review'
        last_key = 'security_concerns'
        data = load_yaml(
            self.prediction.strip(),
            keys_fix_yaml=[
                "ticket_compliance_check",
                "estimated_effort_to_review_[1-5]:",
                "security_concerns:",
                "key_issues_to_review:",
                "relevant_file:",
                "relevant_line:",
                "suggestion:"
            ],
            first_key=first_key,
            last_key=last_key
        )

        comments: List[str] = []
        for suggestion in data.get('code_feedback', []):
            relevant_file = suggestion.get('relevant_file', '').strip()
            relevant_line = suggestion.get('relevant_line', '').strip()
            content = suggestion.get('suggestion', '')

            if not all([relevant_file, relevant_line, content]):
                get_logger().info("Skipping inline comment with missing file/line/content")
                continue

            if self.git_provider.is_supported("create_inline_comment"):
                comment = self.git_provider.create_inline_comment(
                    content,
                    relevant_file,
                    relevant_line
                )
                if comment:
                    comments.append(comment)
            else:
                self.git_provider.publish_inline_comment(
                    content,
                    relevant_file,
                    relevant_line,
                    suggestion
                )

        if comments:
            self.git_provider.publish_inline_comments(comments)

    def _get_user_answers(self) -> Tuple[str, str]:
        """Get Q&A from PR discussion"""
        question_str = ""
        answer_str = ""

        if self.is_answer:
            discussion = self.git_provider.get_issue_comments()

            for message in discussion.reversed:
                if "Questions to better understand the PR:" in message.body:
                    question_str = message.body
                elif '/answer' in message.body:
                    answer_str = message.body

                if answer_str and question_str:
                    break

        return answer_str, question_str

    def _get_previous_review_comment(self):
        """Get previous review comment if it exists"""
        try:
            if hasattr(self.git_provider, "get_previous_review"):
                return self.git_provider.get_previous_review(
                    full=not self.incremental.is_incremental,
                    incremental=self.incremental.is_incremental
                )
        except Exception as e:
            get_logger().exception(f"Failed to get previous review comment: {e}")

    def _remove_previous_review_comment(self, comment) -> None:
        """Remove previous review comment if it exists"""
        try:
            if comment:
                self.git_provider.remove_comment(comment)
        except Exception as e:
            get_logger().exception(f"Failed to remove previous review comment: {e}")

    def _can_run_incremental_review(self) -> bool:
        """Check if incremental review can be run"""
        # Check auto mode
        if self.is_auto and not self.incremental.first_new_commit_sha:
            get_logger().info(f"Incremental review enabled for {self.pr_url} but no new commits")
            return False

        # Check provider support
        if not hasattr(self.git_provider, "get_incremental_commits"):
            get_logger().info(f"Incremental review not supported for {get_settings().config.git_provider}")
            return False

        # Check commit thresholds
        num_new_commits = len(self.incremental.commits_range)
        min_commits = get_settings().pr_reviewer.minimal_commits_for_incremental_review
        not_enough_commits = num_new_commits < min_commits

        # Check timing thresholds
        recent_threshold = datetime.datetime.now() - datetime.timedelta(
            minutes=get_settings().pr_reviewer.minimal_minutes_for_incremental_review
        )
        last_commit_date = (
            self.incremental.last_seen_commit.commit.author.date 
            if self.incremental.last_seen_commit 
            else None
        )
        too_recent = (
            last_commit_date > recent_threshold 
            if self.incremental.last_seen_commit 
            else False
        )

        # Apply threshold logic
        condition = any if get_settings().pr_reviewer.require_all_thresholds_for_incremental_review else all
        if condition((not_enough_commits, too_recent)):
            get_logger().info(
                f"Incremental review enabled for {self.pr_url} but didn't pass thresholds:"
                f"\n* New commits: {num_new_commits} (min: {min_commits})"
                f"\n* Last commit: {last_commit_date} (threshold: {recent_threshold})"
            )
            return False

        return True

    def set_review_labels(self, data: Dict[str, Any]) -> None:
        """Set review labels based on AI analysis"""
        if not get_settings().config.publish_output:
            return

        # Check if we have the required data
        if not get_settings().pr_reviewer.require_estimate_effort_to_review:
            get_settings().pr_reviewer.enable_review_labels_effort = False
        if not get_settings().pr_reviewer.require_security_review:
            get_settings().pr_reviewer.enable_review_labels_security = False

        if not (get_settings().pr_reviewer.enable_review_labels_security or
                get_settings().pr_reviewer.enable_review_labels_effort):
            return

        try:
            review_labels = []

            # Add effort label if enabled
            if get_settings().pr_reviewer.enable_review_labels_effort:
                effort = data['review']['estimated_effort_to_review_[1-5]']
                effort_num = self._parse_effort_value(effort)
                if 1 <= effort_num <= 5:
                    review_labels.append(f'Review effort [1-5]: {effort_num}')

            # Add security label if enabled
            if (get_settings().pr_reviewer.enable_review_labels_security and
                get_settings().pr_reviewer.require_security_review):
                security = data['review']['security_concerns']
                if any(x in security.lower() for x in ['yes', 'true']):
                    review_labels.append('Possible security concern')

            # Update labels
            current_labels = self.git_provider.get_pr_labels(update=True) or []
            get_logger().debug(f"Current labels:\n{current_labels}")

            filtered_labels = [
                label for label in current_labels
                if not label.lower().startswith(('review effort [1-5]:', 'possible security concern'))
            ]

            new_labels = review_labels + filtered_labels
            if (current_labels or review_labels) and sorted(new_labels) != sorted(current_labels):
                get_logger().info(f"Setting review labels:\n{new_labels}")
                self.git_provider.publish_labels(new_labels)
            else:
                get_logger().info(f"Review labels already set:\n{new_labels}")

        except Exception as e:
            get_logger().error(f"Failed to set review labels: {e}")

    def _parse_effort_value(self, effort) -> int:
        """Parse effort value from review data"""
        if isinstance(effort, str):
            try:
                return int(effort.split(',')[0])
            except ValueError:
                get_logger().warning(f"Invalid effort value: {effort}")
                return 0
        elif isinstance(effort, int):
            return effort
        else:
            get_logger().warning(f"Unexpected effort type: {type(effort)}")
            return 0

    def auto_approve_logic(self) -> None:
        """Handle auto-approval logic"""
        if not get_settings().pr_reviewer.enable_auto_approval:
            get_logger().info("Auto-approval disabled")
            self.git_provider.publish_comment(
                "Auto-approval is disabled. Enable via [configuration]"
                "(https://github.com/Khulnasoft/pr-insight/blob/main/docs/REVIEW.md#auto-approval-1)"
            )
            return

        max_effort = get_settings().pr_reviewer.maximal_review_effort
        if max_effort < 5:
            current_labels = self.git_provider.get_pr_labels()
            for label in current_labels:
                if label.lower().startswith('review effort [1-5]:'):
                    effort = int(label.split(':')[1].strip())
                    if effort > max_effort:
                        msg = (
                            f"Auto-approve error: PR review effort ({effort}) exceeds "
                            f"maximum allowed ({max_effort})"
                        )
                        get_logger().info(msg)
                        self.git_provider.publish_comment(msg)
                        return

        if self.git_provider.auto_approve():
            get_logger().info("Auto-approved PR")
            self.git_provider.publish_comment("Auto-approved PR")
