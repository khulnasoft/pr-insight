import asyncio
import json
import os
from typing import Union, Optional, Dict, Any

from pr_insight.insight.pr_insight import PRInsight
from pr_insight.config_loader import get_settings
from pr_insight.git_providers import get_git_provider
from pr_insight.git_providers.utils import apply_repo_settings
from pr_insight.log import get_logger
from pr_insight.servers.github_app import handle_line_comments
from pr_insight.tools.pr_code_suggestions import PRCodeSuggestions
from pr_insight.tools.pr_description import PRDescription
from pr_insight.tools.pr_reviewer import PRReviewer


def is_true(value: Union[str, bool]) -> bool:
    """Check if a value should be considered True."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == 'true'
    return False


def get_setting_or_env(key: str, default: Union[str, bool] = None) -> Union[str, bool]:
    """
    Get a setting from config or environment variables with fallbacks.
    
    Args:
        key: The setting key to look up
        default: Default value if not found
        
    Returns:
        The setting value from config or environment
    """
    try:
        value = get_settings().get(key, default)
    except AttributeError:  # TBD still need to debug why this happens on GitHub Actions
        value = (os.getenv(key) or 
                os.getenv(key.upper()) or 
                os.getenv(key.lower()) or 
                default)
    return value


def get_required_env(name: str) -> Optional[str]:
    """
    Get a required environment variable.
    
    Args:
        name: Name of environment variable
        
    Returns:
        Value if set, None if missing
    """
    value = os.environ.get(name)
    if not value:
        print(f"{name} not set")
        return None
    return value


def setup_openai_config(openai_key: Optional[str], openai_org: Optional[str]) -> None:
    """Configure OpenAI settings."""
    if openai_key:
        get_settings().set("OPENAI.KEY", openai_key)
    else:
        print("OPENAI_KEY not set")
    if openai_org:
        get_settings().set("OPENAI.ORG", openai_org)


async def handle_pr_actions(pr_url: str, auto_review: Optional[bool], 
                          auto_describe: Optional[bool], auto_improve: Optional[bool]) -> None:
    """Handle PR auto actions."""
    get_settings().config.is_auto_command = True
    get_settings().pr_description.final_update_message = False
    
    get_logger().info(
        f"Running auto actions: auto_describe={auto_describe}, "
        f"auto_review={auto_review}, auto_improve={auto_improve}"
    )

    if auto_describe is None or is_true(auto_describe):
        await PRDescription(pr_url).run()
    if auto_review is None or is_true(auto_review):
        await PRReviewer(pr_url).run()
    if auto_improve is None or is_true(auto_improve):
        await PRCodeSuggestions(pr_url).run()


async def handle_comment(event_payload: Dict[str, Any], comment_body: str) -> None:
    """Handle issue/PR comment events."""
    is_pr = False
    disable_eyes = False
    url = None
    
    if event_payload.get("issue", {}).get("pull_request"):
        url = event_payload.get("issue", {}).get("pull_request", {}).get("url")
        is_pr = True
    elif event_payload.get("comment", {}).get("pull_request_url"):
        url = event_payload.get("comment", {}).get("pull_request_url")
        is_pr = True
        disable_eyes = True
    else:
        url = event_payload.get("issue", {}).get("url")

    if url:
        body = comment_body.strip().lower()
        comment_id = event_payload.get("comment", {}).get("id")
        provider = get_git_provider()(pr_url=url)
        
        if is_pr:
            await PRInsight().handle_request(
                url, body, 
                notify=lambda: provider.add_eyes_reaction(
                    comment_id, disable_eyes=disable_eyes
                )
            )
        else:
            await PRInsight().handle_request(url, body)


async def run_action() -> None:
    """Main entry point for GitHub Action."""
    # Get required environment variables
    github_event = get_required_env('GITHUB_EVENT_NAME')
    event_path = get_required_env('GITHUB_EVENT_PATH')
    github_token = get_required_env('GITHUB_TOKEN')
    
    if not all([github_event, event_path, github_token]):
        return

    # Get optional OpenAI config
    openai_key = os.environ.get('OPENAI_KEY') or os.environ.get('OPENAI.KEY')
    openai_org = os.environ.get('OPENAI_ORG') or os.environ.get('OPENAI.ORG')

    # Configure settings
    setup_openai_config(openai_key, openai_org)
    get_settings().set("GITHUB.USER_TOKEN", github_token)
    get_settings().set("GITHUB.DEPLOYMENT_TYPE", "user")
    enable_output = get_setting_or_env("GITHUB_ACTION_CONFIG.ENABLE_OUTPUT", True)
    get_settings().set("GITHUB_ACTION_CONFIG.ENABLE_OUTPUT", enable_output)

    # Load event payload
    try:
        with open(event_path) as f:
            event_payload = json.load(f)
    except json.decoder.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        return

    # Apply repo settings
    try:
        get_logger().info("Applying repo settings")
        pr_url = event_payload.get("pull_request", {}).get("html_url")
        if pr_url:
            apply_repo_settings(pr_url)
            get_logger().info(f"enable_custom_labels: {get_settings().config.enable_custom_labels}")
    except Exception as e:
        get_logger().info(f"github action: failed to apply repo settings: {e}")

    # Handle events
    if github_event == "pull_request":
        action = event_payload.get("action")
        pr_actions = get_settings().get(
            "GITHUB_ACTION_CONFIG.PR_ACTIONS", 
            ["opened", "reopened", "ready_for_review", "review_requested"]
        )

        if action in pr_actions:
            pr_url = event_payload.get("pull_request", {}).get("url")
            if pr_url:
                # Get auto action settings
                auto_review = get_setting_or_env("GITHUB_ACTION.AUTO_REVIEW")
                auto_review = auto_review or get_setting_or_env("GITHUB_ACTION_CONFIG.AUTO_REVIEW")
                
                auto_describe = get_setting_or_env("GITHUB_ACTION.AUTO_DESCRIBE")
                auto_describe = auto_describe or get_setting_or_env("GITHUB_ACTION_CONFIG.AUTO_DESCRIBE")
                
                auto_improve = get_setting_or_env("GITHUB_ACTION.AUTO_IMPROVE")
                auto_improve = auto_improve or get_setting_or_env("GITHUB_ACTION_CONFIG.AUTO_IMPROVE")

                await handle_pr_actions(pr_url, auto_review, auto_describe, auto_improve)
        else:
            get_logger().info(f"Skipping action: {action}")

    elif github_event in ["issue_comment", "pull_request_review_comment"]:
        action = event_payload.get("action")
        if action in ["created", "edited"]:
            comment_body = event_payload.get("comment", {}).get("body")
            try:
                if github_event == "pull_request_review_comment":
                    if '/ask' in comment_body:
                        comment_body = handle_line_comments(event_payload, comment_body)
            except Exception as e:
                get_logger().error(f"Failed to handle line comments: {e}")
                return
                
            if comment_body:
                await handle_comment(event_payload, comment_body)


if __name__ == '__main__':
    asyncio.run(run_action())
