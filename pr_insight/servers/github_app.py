import asyncio.locks
import copy
import os
import re
import uuid
from typing import Any, Dict, Optional, Tuple

import uvicorn
from fastapi import APIRouter, FastAPI, HTTPException, Request, Response
from starlette.background import BackgroundTasks
from starlette.middleware import Middleware
from starlette_context import context
from starlette_context.middleware import RawContextMiddleware

from pr_insight.insight.pr_insight import PRInsight
from pr_insight.algo.utils import update_settings_from_args
from pr_insight.config_loader import get_settings, global_settings
from pr_insight.git_providers import get_git_provider, get_git_provider_with_context
from pr_insight.git_providers.git_provider import IncrementalPR
from pr_insight.git_providers.utils import apply_repo_settings
from pr_insight.identity_providers import get_identity_provider
from pr_insight.identity_providers.identity_provider import Eligibility
from pr_insight.log import LoggingFormat, get_logger, setup_logger
from pr_insight.servers.utils import DefaultDictWithTimeout, verify_signature

# Set up logging
setup_logger(fmt=LoggingFormat.JSON, level="DEBUG")

# Get build number
base_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
build_number_path = os.path.join(base_path, "build_number.txt")
build_number = "unknown"
if os.path.exists(build_number_path):
    with open(build_number_path) as f:
        build_number = f.read().strip()

router = APIRouter()

# Timeouts for duplicate push handling
_duplicate_push_triggers = DefaultDictWithTimeout(ttl=get_settings().github_app.push_trigger_pending_tasks_ttl)
_pending_task_duplicate_push_conditions = DefaultDictWithTimeout(
    asyncio.locks.Condition, 
    ttl=get_settings().github_app.push_trigger_pending_tasks_ttl
)

@router.post("/api/v1/github_webhooks")
async def handle_github_webhooks(
    background_tasks: BackgroundTasks, 
    request: Request,
    response: Response
) -> Dict:
    """
    Handle incoming GitHub webhook requests.
    
    Verifies the request signature, parses the request body, and processes it asynchronously.
    
    Args:
        background_tasks: Background task queue
        request: The incoming HTTP request
        response: The HTTP response
        
    Returns:
        Empty dict on success
    """
    get_logger().debug("Received a GitHub webhook")

    body = await get_body(request)

    # Set up context
    installation_id = body.get("installation", {}).get("id")
    context["installation_id"] = installation_id
    context["settings"] = copy.deepcopy(global_settings)
    context["git_provider"] = {}
    
    # Process webhook asynchronously
    background_tasks.add_task(
        handle_request, 
        body,
        event=request.headers.get("X-GitHub-Event")
    )
    
    return {}

@router.post("/api/v1/marketplace_webhooks") 
async def handle_marketplace_webhooks(request: Request, response: Response) -> None:
    """Handle GitHub Marketplace webhook events"""
    body = await get_body(request)
    get_logger().info(f'Request body:\n{body}')

async def get_body(request: Request) -> Dict:
    """
    Get and validate the request body.
    
    Args:
        request: The incoming HTTP request
        
    Returns:
        Parsed request body as dict
        
    Raises:
        HTTPException: If body parsing fails or signature is invalid
    """
    try:
        body = await request.json()
    except Exception as e:
        get_logger().error("Error parsing request body", e)
        raise HTTPException(status_code=400, detail="Error parsing request body") from e

    # Verify webhook signature if secret configured
    webhook_secret = getattr(get_settings().github, 'webhook_secret', None)
    if webhook_secret:
        body_bytes = await request.body()
        signature = request.headers.get('x-hub-signature-256')
        verify_signature(body_bytes, webhook_secret, signature)
        
    return body

async def handle_comments_on_pr(
    body: Dict[str, Any],
    event: str,
    sender: str, 
    sender_id: str,
    action: str,
    log_context: Dict[str, Any],
    insight: PRInsight
) -> Dict:
    """
    Handle comments posted on pull requests.
    
    Processes command comments starting with "/" and handles line comments.
    
    Args:
        body: Webhook payload
        event: GitHub event type
        sender: GitHub username
        sender_id: GitHub user ID
        action: Webhook action
        log_context: Logging context
        insight: PRInsight instance
        
    Returns:
        Empty dict on success
    """
    if "comment" not in body:
        return {}
        
    comment_body = body.get("comment", {}).get("body", "")
    if not isinstance(comment_body, str):
        return {}
        
    comment_body = comment_body.lstrip()
    if not comment_body.startswith("/"):
        # Handle image comments with /ask
        if '/ask' in comment_body and comment_body.startswith('> ![image]'):
            parts = comment_body.split('/ask')
            comment_body = f'/ask{parts[1]}\n{parts[0].strip().lstrip(">")}'
            get_logger().info(f"Reformatted comment body: {comment_body}")
        else:
            get_logger().info("Ignoring non-command comment")
            return {}

    # Get PR URL
    disable_eyes = False
    if "issue" in body and "pull_request" in body["issue"]:
        api_url = body["issue"]["pull_request"]["url"]
    elif "comment" in body and "pull_request_url" in body["comment"]:
        api_url = body["comment"]["pull_request_url"]
        
        # Handle line comments
        try:
            if ('/ask' in comment_body and
                body["comment"].get("subject_type") == "line"):
                comment_body = handle_line_comments(body, comment_body)
                disable_eyes = True
        except Exception as e:
            get_logger().error(f"Failed to handle line comments: {e}")
    else:
        return {}

    log_context["api_url"] = api_url
    comment_id = body.get("comment", {}).get("id")
    provider = get_git_provider_with_context(pr_url=api_url)

    with get_logger().contextualize(**log_context):
        if get_identity_provider().verify_eligibility(
            "github", sender_id, api_url
        ) is not Eligibility.NOT_ELIGIBLE:
            get_logger().info(
                f"Processing comment on PR {api_url=}, comment_body={comment_body}"
            )
            await insight.handle_request(
                api_url,
                comment_body,
                notify=lambda: provider.add_eyes_reaction(
                    comment_id, 
                    disable_eyes=disable_eyes
                )
            )
        else:
            get_logger().info(
                f"User {sender=} not eligible to process comment on PR {api_url=}"
            )

async def handle_new_pr_opened(
    body: Dict[str, Any],
    event: str,
    sender: str,
    sender_id: str, 
    action: str,
    log_context: Dict[str, Any],
    insight: PRInsight
) -> Dict:
    """
    Handle newly opened pull requests.
    
    Processes PRs based on configured auto-commands.
    
    Args:
        body: Webhook payload
        event: GitHub event type 
        sender: GitHub username
        sender_id: GitHub user ID
        action: Webhook action
        log_context: Logging context
        insight: PRInsight instance
        
    Returns:
        Empty dict on success
    """
    pull_request, api_url = _check_pull_request_event(action, body, log_context)
    if not (pull_request and api_url):
        get_logger().info(f"Invalid PR event: {action=} {api_url=}")
        return {}

    if action in get_settings().github_app.handle_pr_actions:
        apply_repo_settings(api_url)
        if get_identity_provider().verify_eligibility(
            "github", sender_id, api_url
        ) is not Eligibility.NOT_ELIGIBLE:
            await _perform_auto_commands_github(
                "pr_commands",
                insight, 
                body,
                api_url,
                log_context
            )
        else:
            get_logger().info(f"User {sender=} not eligible to process PR {api_url=}")

async def handle_push_trigger_for_new_commits(
    body: Dict[str, Any],
    event: str,
    sender: str,
    sender_id: str,
    action: str, 
    log_context: Dict[str, Any],
    insight: PRInsight
) -> Dict:
    """
    Handle push events with new commits.
    
    Manages duplicate push events and triggers incremental reviews.
    
    Args:
        body: Webhook payload
        event: GitHub event type
        sender: GitHub username
        sender_id: GitHub user ID
        action: Webhook action
        log_context: Logging context
        insight: PRInsight instance
        
    Returns:
        Empty dict on success
    """
    pull_request, api_url = _check_pull_request_event(action, body, log_context)
    if not (pull_request and api_url):
        return {}

    apply_repo_settings(api_url)
    if not get_settings().github_app.handle_push_trigger:
        return {}

    # Check commit SHAs
    before_sha = body.get("before")
    after_sha = body.get("after") 
    merge_commit_sha = pull_request.get("merge_commit_sha")
    
    if before_sha == after_sha:
        return {}
        
    if (get_settings().github_app.push_trigger_ignore_merge_commits and 
        after_sha == merge_commit_sha):
        return {}

    # Handle duplicate push events
    current_active_tasks = _duplicate_push_triggers.setdefault(api_url, 0)
    max_active_tasks = 2 if get_settings().github_app.push_trigger_pending_tasks_backlog else 1
    
    if current_active_tasks >= max_active_tasks:
        get_logger().info(
            f"Skipping push trigger for {api_url=} - another event already triggered processing"
        )
        return {}
        
    get_logger().info(
        f"Processing push trigger for {api_url=} with {current_active_tasks} active tasks"
    )
    _duplicate_push_triggers[api_url] += 1

    async with _pending_task_duplicate_push_conditions[api_url]:
        if current_active_tasks == 1:
            get_logger().info(
                f"Waiting to process push trigger for {api_url=} - first task in progress"
            )
            await _pending_task_duplicate_push_conditions[api_url].wait()
            get_logger().info(f"Continuing push trigger for {api_url=}")

    try:
        if get_identity_provider().verify_eligibility(
            "github", sender_id, api_url
        ) is not Eligibility.NOT_ELIGIBLE:
            get_logger().info(
                f"Performing incremental review for {api_url=} ({event=}, {action=})"
            )
            await _perform_auto_commands_github(
                "push_commands",
                insight,
                body, 
                api_url,
                log_context
            )
    finally:
        async with _pending_task_duplicate_push_conditions[api_url]:
            _pending_task_duplicate_push_conditions[api_url].notify(1)
            _duplicate_push_triggers[api_url] -= 1

def handle_closed_pr(
    body: Dict[str, Any],
    event: str,
    action: str,
    log_context: Dict[str, Any]
) -> None:
    """Log statistics for merged PRs"""
    pull_request = body.get("pull_request", {})
    if not pull_request.get("merged", False):
        return
        
    api_url = pull_request.get("url", "")
    pr_statistics = get_git_provider()(pr_url=api_url).calc_pr_statistics(pull_request)
    log_context["api_url"] = api_url
    
    get_logger().info(
        "PR-Insight statistics for closed PR",
        analytics=True,
        pr_statistics=pr_statistics,
        **log_context
    )

def get_log_context(
    body: Dict[str, Any],
    event: str,
    action: str,
    build_number: str
) -> Tuple[Dict[str, Any], str, str, str]:
    """
    Get logging context and sender info from webhook payload.
    
    Args:
        body: Webhook payload
        event: GitHub event type
        action: Webhook action
        build_number: Application build number
        
    Returns:
        Tuple of (log_context, sender, sender_id, sender_type)
    """
    try:
        sender = body.get("sender", {}).get("login", "")
        sender_id = body.get("sender", {}).get("id", "")
        sender_type = body.get("sender", {}).get("type", "")
        repo = body.get("repository", {}).get("full_name", "")
        git_org = body.get("organization", {}).get("login", "")
        installation_id = body.get("installation", {}).get("id", "")
        app_name = get_settings().get("CONFIG.APP_NAME", "Unknown")
        
        log_context = {
            "action": action,
            "event": event, 
            "sender": sender,
            "server_type": "github_app",
            "request_id": uuid.uuid4().hex,
            "build_number": build_number,
            "app_name": app_name,
            "repo": repo,
            "git_org": git_org,
            "installation_id": installation_id
        }
    except Exception as e:
        get_logger().error("Failed to get log context", e)
        log_context = {}
        sender = ""
        sender_id = ""
        sender_type = ""
        
    return log_context, sender, sender_id, sender_type

def is_bot_user(sender: str, sender_type: str) -> bool:
    """Check if user is a bot that should be ignored"""
    try:
        if (get_settings().get("GITHUB_APP.IGNORE_BOT_PR", False) and 
            sender_type == "Bot" and
            'pr-insight' not in sender):
            get_logger().info(f"Ignoring PR from bot user '{sender}'")
            return True
    except Exception as e:
        get_logger().error(f"Failed 'is_bot_user' check: {e}")
    return False

def should_process_pr_logic(body: Dict[str, Any]) -> bool:
    """
    Check if PR should be processed based on configured rules.
    
    Checks title, labels, source/target branches against ignore patterns.
    
    Args:
        body: Webhook payload
        
    Returns:
        True if PR should be processed, False otherwise
    """
    try:
        pull_request = body.get("pull_request", {})
        title = pull_request.get("title", "")
        pr_labels = pull_request.get("labels", [])
        source_branch = pull_request.get("head", {}).get("ref", "")
        target_branch = pull_request.get("base", {}).get("ref", "")

        # Check title against ignore patterns
        if title:
            ignore_patterns = get_settings().get("CONFIG.IGNORE_PR_TITLE", [])
            if not isinstance(ignore_patterns, list):
                ignore_patterns = [ignore_patterns]
            if ignore_patterns and any(re.search(p, title) for p in ignore_patterns):
                get_logger().info(f"Ignoring PR with title '{title}' - matches ignore pattern")
                return False

        # Check labels
        ignore_labels = get_settings().get("CONFIG.IGNORE_PR_LABELS", [])
        if pr_labels and ignore_labels:
            labels = [label['name'] for label in pr_labels]
            if any(label in ignore_labels for label in labels):
                get_logger().info(
                    f"Ignoring PR with labels '{', '.join(labels)}' - matches ignore list"
                )
                return False

        # Check branches
        ignore_source = get_settings().get("CONFIG.IGNORE_PR_SOURCE_BRANCHES", [])
        ignore_target = get_settings().get("CONFIG.IGNORE_PR_TARGET_BRANCHES", [])
        
        if pull_request and (ignore_source or ignore_target):
            if any(re.search(p, source_branch) for p in ignore_source):
                get_logger().info(
                    f"Ignoring PR from source branch '{source_branch}' - matches pattern"
                )
                return False
                
            if any(re.search(p, target_branch) for p in ignore_target):
                get_logger().info(
                    f"Ignoring PR to target branch '{target_branch}' - matches pattern"
                )
                return False
                
    except Exception as e:
        get_logger().error(f"Failed 'should_process_pr_logic': {e}")
        
    return True

async def handle_request(body: Dict[str, Any], event: str) -> Dict:
    """
    Main webhook request handler.
    
    Routes requests to appropriate handlers based on event type and action.
    
    Args:
        body: Webhook payload
        event: GitHub event type
        
    Returns:
        Empty dict on success
    """
    action = body.get("action")
    if not action:
        return {}
        
    insight = PRInsight()
    log_context, sender, sender_id, sender_type = get_log_context(
        body, event, action, build_number
    )

    # Check if request should be processed
    if is_bot_user(sender, sender_type) and 'check_run' not in body:
        return {}
    if action != 'created' and 'check_run' not in body:
        if not should_process_pr_logic(body):
            return {}

    # Route to appropriate handler
    if 'check_run' in body:
        pass # Handle failed checks
    elif action == 'created':
        get_logger().debug('Request body', artifact=body, event=event)
        await handle_comments_on_pr(
            body, event, sender, sender_id, action, log_context, insight
        )
    elif event == 'pull_request':
        if action == 'synchronize':
            await handle_push_trigger_for_new_commits(
                body, event, sender, sender_id, action, log_context, insight
            )
        elif action == 'closed':
            if get_settings().get("CONFIG.ANALYTICS_FOLDER"):
                handle_closed_pr(body, event, action, log_context)
        elif action != 'synchronize':
            get_logger().debug('Request body', artifact=body, event=event)
            await handle_new_pr_opened(
                body, event, sender, sender_id, action, log_context, insight
            )
    elif event == "issue_comment" and action == 'edited':
        pass # Handle checkbox clicked
    else:
        get_logger().info(f"No handler for {event=} {action=}")
        
    return {}

def handle_line_comments(body: Dict[str, Any], comment_body: str) -> str:
    """
    Format line comments for processing.
    
    Args:
        body: Comment webhook payload
        comment_body: Original comment text
        
    Returns:
        Formatted comment command
    """
    if not comment_body:
        return ""
        
    start_line = body["comment"]["start_line"] or body["comment"]["line"]
    end_line = body["comment"]["line"]
    question = comment_body.replace('/ask', '').strip()
    
    get_settings().set("ask_diff_hunk", body["comment"]["diff_hunk"])
    
    if '/ask' in comment_body:
        comment_body = (
            f"/ask_line "
            f"--line_start={start_line} "
            f"--line_end={end_line} "
            f"--side={body['comment']['side']} "
            f"--file_name={body['comment']['path']} "
            f"--comment_id={body['comment']['id']} "
            f"{question}"
        )
        
    return comment_body

def _check_pull_request_event(
    action: str,
    body: Dict[str, Any],
    log_context: Dict[str, Any]
) -> Tuple[Dict[str, Any], str]:
    """
    Validate pull request event.
    
    Args:
        action: Webhook action
        body: Webhook payload
        log_context: Logging context
        
    Returns:
        Tuple of (pull_request_data, api_url)
    """
    pull_request = body.get("pull_request", {})
    if not pull_request:
        return {}, ""
        
    api_url = pull_request.get("url", "")
    if not api_url:
        return {}, ""
        
    log_context["api_url"] = api_url
    
    if (pull_request.get("draft", True) or 
        pull_request.get("state") != "open"):
        return {}, ""
        
    if (action in ("review_requested", "synchronize") and
        pull_request.get("created_at") == pull_request.get("updated_at")):
        return {}, ""
        
    return pull_request, api_url

async def _perform_auto_commands_github(
    commands_conf: str,
    insight: PRInsight,
    body: Dict[str, Any],
    api_url: str,
    log_context: Dict[str, Any]
) -> Optional[Dict]:
    """
    Execute configured automatic commands.
    
    Args:
        commands_conf: Name of commands config section
        insight: PRInsight instance
        body: Webhook payload
        api_url: PR API URL
        log_context: Logging context
        
    Returns:
        Empty dict or None
    """
    apply_repo_settings(api_url)
    if not should_process_pr_logic(body):
        return {}
        
    commands = get_settings().get(f"github_app.{commands_conf}")
    if not commands:
        get_logger().info("No auto commands configured")
        return
        
    get_settings().set("config.is_auto_command", True)
    
    for command in commands:
        parts = command.split()
        cmd = parts[0]
        args = parts[1:]
        other_args = update_settings_from_args(args)
        new_command = ' '.join([cmd] + other_args)
        
        get_logger().info(
            f"{commands_conf}: Running auto command '{new_command}' for {api_url=}"
        )
        await insight.handle_request(api_url, new_command)

@router.get("/")
async def root() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "ok"}

# Configure app
if get_settings().github_app.override_deployment_type:
    get_settings().set("GITHUB.DEPLOYMENT_TYPE", "app")
    
middleware = [Middleware(RawContextMiddleware)]
app = FastAPI(middleware=middleware)
app.include_router(router)

def start() -> None:
    """Start the FastAPI server"""
    port = int(os.environ.get("PORT", "3000"))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == '__main__':
    start()
