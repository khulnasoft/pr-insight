import re
import traceback

from pr_insight.config_loader import get_settings
from pr_insight.git_providers import GithubProvider
from pr_insight.log import get_logger


tickets = {next((m for m in reversed(match) if m), None) if isinstance(match, tuple) else match
           for pattern in patterns
           for match in re.findall(pattern, text)
           if match}

    return list(tickets)


def extract_ticket_links_from_pr_description(pr_description, repo_path):
    """
    Extract all ticket links from PR description
    """
    github_tickets = []
    try:
        # example link to search for: https://github.com/khulnasoft/pr-insight-pro/issues/525
        pattern = r'https://github[^/]+/[^/]+/[^/]+/issues/\d+' # should support also github server (for example 'https://github.company.ai/khulnasoft/pr-insight-pro/issues/525')

        # Find all matches in the text
        github_tickets = re.findall(pattern, pr_description)

        # Find all issues referenced like #123 and add them as https://github.com/{repo_path}/issues/{issue_number}
        issue_number_pattern = r'#\d+'
        issue_numbers = re.findall(issue_number_pattern, pr_description)
        for issue_number in issue_numbers:
            issue_number = issue_number[1:]  # remove #
            # check if issue_number is a valid number and len(issue_number) < 5
            if issue_number.isdigit() and len(issue_number) < 5:
                github_tickets.append(f'https://github.com/{repo_path}/issues/{issue_number}')
    except Exception as e:
        get_logger().error(f"Error extracting tickets error= {e}",
                           artifact={"traceback": traceback.format_exc()})

    return github_tickets


async def extract_tickets(git_provider):
    MAX_TICKET_CHARACTERS = 10000
    try:
        if isinstance(git_provider, GithubProvider):
            user_description = git_provider.get_user_description()
            tickets = extract_ticket_links_from_pr_description(user_description, git_provider.repo)
            tickets_content = []
            if tickets:
                for ticket in tickets:
                    # extract ticket number and repo name
                    repo_name, original_issue_number = git_provider._parse_issue_url(ticket)

                    # get the ticket object
                    try:
                        issue_main = git_provider.repo_obj.get_issue(original_issue_number)
                    except Exception as e:
                        get_logger().error(f"Error getting issue_main error= {e}",
                                           artifact={"traceback": traceback.format_exc()})
                        continue

                    # clip issue_main.body max length
                    issue_body_str = issue_main.body or ""

                    if len(issue_body_str) > MAX_TICKET_CHARACTERS:
                        issue_body_str = issue_body_str[:MAX_TICKET_CHARACTERS] + "..."

                    # extract labels
                    labels = []
                    try:
                        for label in issue_main.labels:
                            if isinstance(label, str):
                                labels.append(label)
                            else:
                                labels.append(label.name)
                    except Exception as e:
                        get_logger().error(f"Error extracting labels error= {e}",
                                           artifact={"traceback": traceback.format_exc()})
                    tickets_content.append(
                        {'ticket_id': issue_main.number,
                         'ticket_url': ticket, 'title': issue_main.title, 'body': issue_body_str,
                         'labels': ", ".join(labels)})
                return tickets_content

    except Exception as e:
        get_logger().error(f"Error extracting tickets error= {e}",
                           artifact={"traceback": traceback.format_exc()})


async def extract_and_cache_pr_tickets(git_provider, vars):
    if get_settings().get('config.require_ticket_analysis_review', False):
        return
    related_tickets = get_settings().get('related_tickets', [])
    if not related_tickets:
        tickets_content = await extract_tickets(git_provider)
        if tickets_content:
            get_logger().info("Extracted tickets from PR description", artifact={"tickets": tickets_content})
            vars['related_tickets'] = tickets_content
            get_settings().set('related_tickets', tickets_content)
    else:  # if tickets are already cached
        get_logger().info("Using cached tickets", artifact={"tickets": related_tickets})
        vars['related_tickets'] = related_tickets


def check_tickets_relevancy():
    return True
