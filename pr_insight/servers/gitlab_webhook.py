import copy
import re
import json
from datetime import datetime
from typing import Dict, Any, Optional

import uvicorn
from fastapi import APIRouter, FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.background import BackgroundTasks
from starlette.middleware import Middleware
from starlette_context import context
from starlette_context.middleware import RawContextMiddleware

from pr_insight.insight.pr_insight import PRInsight
from pr_insight.algo.utils import update_settings_from_args
from pr_insight.config_loader import get_settings, global_settings
from pr_insight.git_providers.utils import apply_repo_settings
from pr_insight.log import LoggingFormat, get_logger, setup_logger
from pr_insight.secret_providers import get_secret_provider

# Configure logging
setup_logger(fmt=LoggingFormat.JSON, level="DEBUG")

# Initialize router and secret provider
router = APIRouter()
secret_provider = get_secret_provider() if get_settings().get("CONFIG.SECRET_PROVIDER") else None


async def get_mr_url_from_commit_sha(commit_sha: str, gitlab_token: str, project_id: int) -> Optional[str]:
    """
    Get merge request URL from a commit SHA.
    
    Args:
        commit_sha: The commit SHA to look up
        gitlab_token: GitLab API token
        project_id: GitLab project ID
        
    Returns:
        The merge request URL if found, None otherwise
    """
    try:
        import requests
        headers = {'Private-Token': gitlab_token}
        gitlab_url = get_settings().get("GITLAB.URL", 'https://gitlab.com')
        
        response = requests.get(
            f'{gitlab_url}/api/v4/projects/{project_id}/repository/commits/{commit_sha}/merge_requests',
            headers=headers
        )
        
        if response.status_code == 200 and response.json():
            return response.json()[0]['web_url']
            
        get_logger().info(f"No merge requests found for commit: {commit_sha}")
        return None
        
    except Exception as e:
        get_logger().error(f"Failed to get MR url from commit sha: {e}")
        return None


async def handle_request(api_url: str, body: str, log_context: dict, sender_id: str) -> None:
    """Handle an incoming webhook request."""
    log_context.update({
        "action": body,
        "event": "pull_request" if body == "/review" else "comment", 
        "api_url": api_url,
        "app_name": get_settings().get("CONFIG.APP_NAME", "Unknown")
    })

    with get_logger().contextualize(**log_context):
        await PRInsight().handle_request(api_url, body)


async def _perform_commands_gitlab(
    commands_conf: str, 
    insight: PRInsight, 
    api_url: str,
    log_context: dict, 
    data: dict
) -> None:
    """Execute configured GitLab commands."""
    apply_repo_settings(api_url)
    if not should_process_pr_logic(data):
        return
        
    commands = get_settings().get(f"gitlab.{commands_conf}", {})
    get_settings().set("config.is_auto_command", True)
    
    for command in commands:
        try:
            split_command = command.split(" ")
            base_command = split_command[0]
            args = split_command[1:]
            other_args = update_settings_from_args(args)
            full_command = ' '.join([base_command] + other_args)
            
            get_logger().info(f"Performing command: {full_command}")
            with get_logger().contextualize(**log_context):
                await insight.handle_request(api_url, full_command)
                
        except Exception as e:
            get_logger().error(f"Failed to perform command {command}: {e}")


def is_bot_user(data: Dict[str, Any]) -> bool:
    """Check if the user is a bot based on username patterns."""
    try:
        sender_name = data.get("user", {}).get("name", "unknown").lower()
        bot_indicators = ['khulnasoft', 'bot_', 'bot-', '_bot', '-bot']
        
        if any(indicator in sender_name for indicator in bot_indicators):
            get_logger().info(f"Skipping GitLab bot user: {sender_name}")
            return True
            
    except Exception as e:
        get_logger().error(f"Failed 'is_bot_user' logic: {e}")
        
    return False


def should_process_pr_logic(data: Dict[str, Any]) -> bool:
    """
    Determine if a merge request should be processed based on configured rules.
    
    Checks title, labels, source/target branches against ignore patterns.
    """
    try:
        if not data.get('object_attributes', {}):
            return False
            
        title = data['object_attributes'].get('title')
        settings = get_settings()

        # Get ignore patterns from settings
        ignore_patterns = {
            'title': settings.get("CONFIG.IGNORE_PR_TITLE", []),
            'labels': settings.get("CONFIG.IGNORE_PR_LABELS", []),
            'source_branches': settings.get("CONFIG.IGNORE_PR_SOURCE_BRANCHES", []),
            'target_branches': settings.get("CONFIG.IGNORE_PR_TARGET_BRANCHES", [])
        }

        # Check source branch
        if ignore_patterns['source_branches']:
            source_branch = data['object_attributes'].get('source_branch')
            if any(re.search(regex, source_branch) for regex in ignore_patterns['source_branches']):
                get_logger().info(
                    f"Ignoring MR with source branch '{source_branch}' due to gitlab.ignore_mr_source_branches settings")
                return False

        # Check target branch
        if ignore_patterns['target_branches']:
            target_branch = data['object_attributes'].get('target_branch')
            if any(re.search(regex, target_branch) for regex in ignore_patterns['target_branches']):
                get_logger().info(
                    f"Ignoring MR with target branch '{target_branch}' due to gitlab.ignore_mr_target_branches settings")
                return False

        # Check labels
        if ignore_patterns['labels']:
            labels = [label['title'] for label in data['object_attributes'].get('labels', [])]
            if any(label in ignore_patterns['labels'] for label in labels):
                get_logger().info(f"Ignoring MR with labels '{', '.join(labels)}' due to gitlab.ignore_mr_labels settings")
                return False

        # Check title
        if ignore_patterns['title']:
            if any(re.search(regex, title) for regex in ignore_patterns['title']):
                get_logger().info(f"Ignoring MR with title '{title}' due to gitlab.ignore_mr_title settings")
                return False
                
    except Exception as e:
        get_logger().error(f"Failed 'should_process_pr_logic': {e}")
        
    return True


@router.post("/webhook")
async def gitlab_webhook(background_tasks: BackgroundTasks, request: Request) -> JSONResponse:
    """Handle incoming GitLab webhook requests."""
    start_time = datetime.now()
    request_json = await request.json()
    context["settings"] = copy.deepcopy(global_settings)

    async def inner(data: dict) -> JSONResponse:
        log_context = {"server_type": "gitlab_app"}
        get_logger().debug("Received a GitLab webhook")

        # Validate webhook token
        if request.headers.get("X-Gitlab-Token") and secret_provider:
            request_token = request.headers.get("X-Gitlab-Token")
            secret = secret_provider.get_secret(request_token)
            
            if not secret:
                get_logger().warning(f"Empty secret retrieved, request_token: {request_token}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content=jsonable_encoder({"message": "unauthorized"})
                )
                
            try:
                secret_dict = json.loads(secret)
                gitlab_token = secret_dict["gitlab_token"]
                log_context["token_id"] = secret_dict.get("token_name", secret_dict.get("id", "unknown"))
                context["settings"].gitlab.personal_access_token = gitlab_token
                
            except Exception as e:
                get_logger().error(f"Failed to validate secret {request_token}: {e}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content=jsonable_encoder({"message": "unauthorized"})
                )
                
        elif get_settings().get("GITLAB.SHARED_SECRET"):
            secret = get_settings().get("GITLAB.SHARED_SECRET")
            if request.headers.get("X-Gitlab-Token") != secret:
                get_logger().error("Failed to validate secret")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content=jsonable_encoder({"message": "unauthorized"})
                )
                
        else:
            get_logger().error("Failed to validate secret")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=jsonable_encoder({"message": "unauthorized"})
            )

        gitlab_token = get_settings().get("GITLAB.PERSONAL_ACCESS_TOKEN")
        if not gitlab_token:
            get_logger().error("No gitlab token found")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=jsonable_encoder({"message": "unauthorized"})
            )

        get_logger().info("GitLab data", artifact=data)
        sender = data.get("user", {}).get("username", "unknown")
        sender_id = data.get("user", {}).get("id", "unknown")

        # Skip bot users and filtered MRs
        if is_bot_user(data):
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=jsonable_encoder({"message": "success"})
            )
            
        if data.get('event_type') != 'note' and not should_process_pr_logic(data):
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=jsonable_encoder({"message": "success"})
            )

        log_context["sender"] = sender

        # Handle merge request events
        if (data.get('object_kind') == 'merge_request' and 
            data['object_attributes'].get('action') in ['open', 'reopen']):
            
            url = data['object_attributes'].get('url')
            draft = data['object_attributes'].get('draft')
            
            get_logger().info(f"New merge request: {url}")
            
            if draft:
                get_logger().info(f"Skipping draft MR: {url}")
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content=jsonable_encoder({"message": "success"})
                )

            await _perform_commands_gitlab("pr_commands", PRInsight(), url, log_context, data)

        # Handle comment events
        elif data.get('object_kind') == 'note' and data.get('event_type') == 'note':
            if 'merge_request' in data:
                mr = data['merge_request']
                url = mr.get('url')

                get_logger().info(f"A comment has been added to a merge request: {url}")
                body = data.get('object_attributes', {}).get('note')
                
                if (data.get('object_attributes', {}).get('type') == 'DiffNote' and 
                    '/ask' in body):
                    body = handle_ask_line(body, data)

                await handle_request(url, body, log_context, sender_id)

        # Handle push events
        elif data.get('object_kind') == 'push' and data.get('event_name') == 'push':
            try:
                project_id = data['project_id']
                commit_sha = data['checkout_sha']
                url = await get_mr_url_from_commit_sha(commit_sha, gitlab_token, project_id)
                
                if not url:
                    get_logger().info(f"No MR found for commit: {commit_sha}")
                    return JSONResponse(
                        status_code=status.HTTP_200_OK,
                        content=jsonable_encoder({"message": "success"})
                    )

                # Apply repo settings and check push commands
                apply_repo_settings(url)
                commands_on_push = get_settings().get("gitlab.push_commands", {})
                handle_push_trigger = get_settings().get("gitlab.handle_push_trigger", False)
                
                if not commands_on_push or not handle_push_trigger:
                    get_logger().info("Push event, but no push commands found or push trigger is disabled")
                    return JSONResponse(
                        status_code=status.HTTP_200_OK,
                        content=jsonable_encoder({"message": "success"})
                    )

                get_logger().debug(f'A push event has been received: {url}')
                await _perform_commands_gitlab("push_commands", PRInsight(), url, log_context, data)
                
            except Exception as e:
                get_logger().error(f"Failed to handle push event: {e}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({"message": "success"})
        )

    background_tasks.add_task(inner, request_json)
    end_time = datetime.now()
    get_logger().info(f"Processing time: {end_time - start_time}", request=request_json)
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=jsonable_encoder({"message": "success"})
    )


def handle_ask_line(body: str, data: Dict[str, Any]) -> str:
    """Process an /ask line comment to include line number and file information."""
    try:
        line_range = data['object_attributes']['position']['line_range']
        start_line = line_range['start']['new_line']
        end_line = line_range['end']['new_line']
        path = data['object_attributes']['position']['new_path']
        comment_id = data['object_attributes']["discussion_id"]
        
        get_logger().info("Handling line comment")
        
        return (f"/ask_line --line_start={start_line} --line_end={end_line} "
                f"--side=RIGHT --file_name={path} --comment_id={comment_id} "
                f"{body.replace('/ask', '').strip()}")
                
    except Exception as e:
        get_logger().error(f"Failed to handle ask line comment: {e}")
        return body


@router.get("/")
async def root() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


# Configure GitLab URL and app settings
gitlab_url = get_settings().get("GITLAB.URL")
if not gitlab_url:
    raise ValueError("GITLAB.URL is not set")
    
get_settings().config.git_provider = "gitlab"

# Initialize FastAPI app with middleware
middleware = [Middleware(RawContextMiddleware)]
app = FastAPI(middleware=middleware)
app.include_router(router)


def start() -> None:
    """Start the FastAPI server."""
    uvicorn.run(app, host="0.0.0.0", port=3000)


if __name__ == '__main__':
    start()
