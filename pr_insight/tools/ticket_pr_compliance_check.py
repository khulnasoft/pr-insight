import re
import traceback
from pr_insight.config_loader import get_settings
from pr_insight.git_providers import GithubProvider
from pr_insight.log import get_logger


def extract_ticket_links_from_pr_description(pr_description: str, repo_path: str) -> list:
    """
    Extract all ticket links from the PR description.
    """
    github_tickets = []
    try:
        # Pattern to match GitHub issue URLs
        pattern = r'https://github(?:\.com|\.company\.ai)/[^/]+/[^/]+/issues/\d+'
        github_tickets = re.findall(pattern, pr_description)

        # Find issues referenced like #123 and add them as URLs
        issue_numbers = re.findall(r'#(\d+)', pr_description)  # Using capturing group to simplify extraction
        for issue_number in issue_numbers:
            # Check if issue_number is valid
            if len(issue_number) < 5:  # No need for isdigit() as we extract only digits
                github_tickets.append(f'https://github.com/{repo_path}/issues/{issue_number}')
    except Exception as e:
        get_logger().error(
            f"Error extracting tickets: {e}",
            artifact={"traceback": traceback.format_exc()}
        )

    return github_tickets


async def extract_tickets(git_provider: GithubProvider) -> list:
    MAX_TICKET_CHARACTERS = 10000
    tickets_content = []

    try:
        if isinstance(git_provider, GithubProvider):
            user_description = git_provider.get_user_description()
            tickets = extract_ticket_links_from_pr_description(user_description, git_provider.repo)

            for ticket in tickets:
                repo_name, original_issue_number = git_provider._parse_issue_url(ticket)

                try:
                    issue_main = git_provider.repo_obj.get_issue(original_issue_number)
                    issue_body_str = issue_main.body or ""

                    # Clip issue_main.body to MAX_TICKET_CHARACTERS
                    issue_body_str = (issue_body_str[:MAX_TICKET_CHARACTERS] + "...") if len(issue_body_str) > MAX_TICKET_CHARACTERS else issue_body_str

                    # Extract labels
                    labels = [label.name if not isinstance(label, str) else label for label in issue_main.labels]

                    tickets_content.append({
                        'ticket_id': issue_main.number,
                        'ticket_url': ticket,
                        'title': issue_main.title,
                        'body': issue_body_str,
                        'labels': ", ".join(labels)
                    })

                except Exception as e:
                    get_logger().error(
                        f"Error getting issue {original_issue_number}: {e}",
                        artifact={"traceback": traceback.format_exc()}
                    )
    except Exception as e:
        get_logger().error(
            f"Error extracting tickets: {e}",
            artifact={"traceback": traceback.format_exc()}
        )

    return tickets_content


async def extract_and_cache_pr_tickets(git_provider: GithubProvider, vars: dict):
    if get_settings().get('config.require_ticket_analysis_review', False):
        return

    related_tickets = get_settings().get('related_tickets', [])
    if not related_tickets:
        tickets_content = await extract_tickets(git_provider)
        if tickets_content:
            get_logger().info("Extracted tickets from PR description", artifact={"tickets": tickets_content})
            vars['related_tickets'] = tickets_content
            get_settings().set('related_tickets', tickets_content)
    else:
        get_logger().info("Using cached tickets", artifact={"tickets": related_tickets})
        vars['related_tickets'] = related_tickets


def check_tickets_relevancy() -> bool:
    return True
