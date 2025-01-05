import argparse
import asyncio
import os

from pr_insight.algo.utils import get_version
from pr_insight.config_loader import get_settings
from pr_insight.insight.pr_insight import PRInsight, commands
from pr_insight.log import get_logger, setup_logger

log_level = os.environ.get("LOG_LEVEL", "INFO")
setup_logger(log_level)


def set_parser():
    parser = argparse.ArgumentParser(description='AI based pull request analyzer', usage=
    """\
    Usage: cli.py --pr-url=<URL on supported git hosting service> <command> [<args>].
    For example:
    - cli.py --pr_url=... review
    - cli.py --pr_url=... describe
    - cli.py --pr_url=... improve
    - cli.py --pr_url=... ask "write me a poem about this PR"
    - cli.py --pr_url=... reflect
    - cli.py --issue_url=... similar_issue

    Supported commands:
    - review / review_pr - Add a review that includes a summary of the PR and specific suggestions for improvement.

    - ask / ask_question [question] - Ask a question about the PR.

    - describe / describe_pr - Modify the PR title and description based on the PR's contents.

    - improve / improve_code - Suggest improvements to the code in the PR as pull request comments ready to commit.
    Extended mode ('improve --extended') employs several calls, and provides a more thorough feedback

    - reflect - Ask the PR author questions about the PR.

    - update_changelog - Update the changelog based on the PR's contents.

    - add_docs

    - generate_labels


    Configuration:
    To edit any configuration parameter from 'configuration.toml', just add -config_path=<value>.
    For example: 'python cli.py --pr_url=... review --pr_reviewer.extra_instructions="focus on the file: ..."'
    """)
    parser.add_argument('--version', action='version', version=f'pr-insight {get_version()}')
    parser.add_argument('--pr_url', type=str, help='The URL of the PR to review', default=None)
    parser.add_argument('--issue_url', type=str, help='The URL of the Issue to review', default=None)
    parser.add_argument('command', type=str, help='The', choices=commands, default='review')
    parser.add_argument('rest', nargs=argparse.REMAINDER, default=[])
    return parser


def run_command(pr_url, command):
    # Preparing the command
    run_command_str = f"--pr_url={pr_url} {command.lstrip('/')}"
    args = set_parser().parse_args(run_command_str.split())

    # Run the command. Feedback will appear in GitHub PR comments
    run(args=args)


def run(inargs=None, args=None):
    parser = set_parser()
    if not args:
        args = parser.parse_args(inargs)
    if not args.pr_url and not args.issue_url:
        parser.print_help()
        return

    command = args.command.lower()
    get_settings().set("CONFIG.CLI_MODE", True)

    async def inner():
        if args.issue_url:
            result = await asyncio.create_task(PRInsight().handle_request(args.issue_url, [command] + args.rest))
        else:
            result = await asyncio.create_task(PRInsight().handle_request(args.pr_url, [command] + args.rest))

        if get_settings().litellm.get("enable_callbacks", False):
            # There may be additional events on the event queue from the run above. If there are give them time to complete.
            get_logger().debug("Waiting for event queue to complete")
            await asyncio.wait([task for task in asyncio.all_tasks() if task is not asyncio.current_task()])

        return result

    result = asyncio.run(inner())
    if not result:
        parser.print_help()


if __name__ == '__main__':
    run()
