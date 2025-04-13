import argparse
import asyncio
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import (BarColumn, Progress, SpinnerColumn, TextColumn,
                           TimeRemainingColumn)
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from pr_insight.algo.utils import get_version
from pr_insight.config_loader import get_settings
from pr_insight.insight.pr_insight import PRInsight, commands
from pr_insight.log import get_logger, setup_logger

# Constants
DEFAULT_LOG_LEVEL = "INFO"
CONFIG_CLI_MODE = "CONFIG.CLI_MODE"

# Color theme
PR_INSIGHT_THEME = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "highlight": "magenta",
    "command": "bold cyan",
    "url": "underline blue",
    "header": "bold white on blue",
})

# Initialize rich console
console = Console(theme=PR_INSIGHT_THEME)

# ASCII art banner
PR_INSIGHT_BANNER = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ██████╗ ██████╗       ██╗███╗   ██╗███████╗██╗ ██████╗ ██╗  ║
║   ██╔══██╗██╔══██╗      ██║████╗  ██║██╔════╝██║██╔════╝ ██║  ║
║   ██████╔╝██████╔╝█████╗██║██╔██╗ ██║███████╗██║██║  ███╗██║  ║
║   ██╔═══╝ ██╔══██╗╚════╝██║██║╚██╗██║╚════██║██║██║   ██║██║  ║
║   ██║     ██║  ██║      ██║██║ ╚████║███████║██║╚██████╔╝██║  ║
║   ╚═╝     ╚═╝  ╚═╝      ╚═╝╚═╝  ╚═══╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""

# Configure logging
log_level = os.environ.get("LOG_LEVEL", DEFAULT_LOG_LEVEL)
logger = get_logger()
setup_logger(log_level)


def set_parser() -> argparse.ArgumentParser:
    """
    Create and configure the command-line argument parser.

    This function sets up the command-line interface for the PR-Insight tool,
    including all available commands and their descriptions.

    Returns:
        argparse.ArgumentParser: Configured parser ready to parse command line arguments
    """
    # Create a custom argparse formatter that delegates to rich for formatting
    class RichHelpFormatter(argparse.HelpFormatter):
        def __init__(self, prog):
            super().__init__(prog, max_help_position=40, width=100)

        def format_help(self):
            # Let argparse generate the help text
            help_text = super().format_help()
            return help_text  # Will be formatted by rich elsewhere

    parser = argparse.ArgumentParser(
        description="AI-based pull request analyzer and assistant",
        formatter_class=RichHelpFormatter,
        usage="""\
    Usage: cli.py --pr-url=<URL on supported git hosting service> <command> [<args>].
    For example:
    - cli.py --pr_url=... review
    - cli.py --pr_url=... describe
    - cli.py --pr_url=... improve
    - cli.py --pr_url=... ask "write me a poem about this PR"
    - cli.py --pr_url=... reflect
    - cli.py --issue_url=... similar_issue
    """,
    )
    parser.add_argument("--version", action="version", version=f"pr-insight {get_version()}",
                       help="Show program's version number and exit")
    parser.add_argument("--pr_url", type=str, help="The URL of the pull request to analyze", default=None)
    parser.add_argument("--issue_url", type=str, help="The URL of the issue to analyze", default=None)
    parser.add_argument("command", type=str, help="The command to execute", choices=commands, default="review")
    parser.add_argument("rest", nargs=argparse.REMAINDER, help="Additional arguments specific to the command", default=[])
    return parser


def display_rich_help():
    """
    Display a formatted, colorful help message with command descriptions and examples.
    """
    console.print(Panel.fit(PR_INSIGHT_BANNER, border_style="cyan"))
    console.print("\n[bold cyan]PR-Insight[/] - [italic]AI-based pull request analyzer and assistant[/]\n")

    # Command examples
    console.print("[header]EXAMPLE USAGE[/header]")
    examples_table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
    examples_table.add_column("Command")
    examples_table.add_column("Description")

    examples_table.add_row("cli.py --pr_url=... [command]review[/command]", "Add a review with summary and suggestions")
    examples_table.add_row("cli.py --pr_url=... [command]describe[/command]", "Modify PR title and description")
    examples_table.add_row("cli.py --pr_url=... [command]improve[/command]", "Suggest code improvements")
    examples_table.add_row("cli.py --pr_url=... [command]ask[/command] \"question\"", "Ask a question about the PR")
    examples_table.add_row("cli.py --pr_url=... [command]reflect[/command]", "Ask PR author questions")
    examples_table.add_row("cli.py --issue_url=... [command]similar_issue[/command]", "Find similar issues")

    console.print(examples_table)
    console.print()

    # Available commands
    console.print("[header]AVAILABLE COMMANDS[/header]")
    commands_table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
    commands_table.add_column("Command", style="cyan")
    commands_table.add_column("Description")

    commands_table.add_row("review / review_pr", "Add a review that includes a summary of the PR and specific suggestions.")
    commands_table.add_row("ask / ask_question", "Ask a question about the PR.")
    commands_table.add_row("describe / describe_pr", "Modify the PR title and description based on the PR's contents.")
    commands_table.add_row("improve / improve_code", "Suggest improvements to the code in the PR as comments ready to commit.\nExtended mode ('improve --extended') provides more thorough feedback.")
    commands_table.add_row("reflect", "Ask the PR author questions about the PR.")
    commands_table.add_row("update_changelog", "Update the changelog based on the PR's contents.")
    commands_table.add_row("add_docs", "Generate or update documentation based on the PR's contents.")
    commands_table.add_row("generate_labels", "Suggest appropriate labels for the PR based on its contents.")

    console.print(commands_table)
    console.print()

    # Configuration
    console.print("[header]CONFIGURATION[/header]")
    console.print("To edit any configuration parameter from 'configuration.toml', add -config_path=<value>.")
    console.print("Example: [italic]python cli.py --pr_url=... review --pr_reviewer.extra_instructions=\"focus on the file: ...\"[/italic]\n")

    # Version information
    console.print(f"[bold]PR-Insight v{get_version()}[/]")


def run_command(pr_url: str, command: str) -> None:
    """
    Execute a PR Insight command on a specific pull request URL.

    This function provides a programmatic interface to run PR Insight commands
    without using command-line arguments directly.

    Args:
        pr_url: The URL of the pull request to analyze
        command: The PR Insight command to execute

    Returns:
        None

    Raises:
        ValueError: If the pr_url is empty or None
        ValueError: If the command is not supported
    """
    if not pr_url:
        raise ValueError("Pull request URL cannot be empty")

    if not command:
        raise ValueError("Command cannot be empty")

    # Normalize the command by removing leading slashes
    normalized_command = command.lstrip('/')

    # Make sure the command is supported
    if normalized_command not in commands:
        raise ValueError(f"Unsupported command: {command}. Available commands: {', '.join(commands)}")

    # Preparing the command string
    run_command_str = f"--pr_url={pr_url} {normalized_command}"

    try:
        # Parse the command into arguments
        args = set_parser().parse_args(run_command_str.split())

        # Run the command. Feedback will appear in GitHub PR comments
        console.print(f"Running command [command]'{normalized_command}'[/command] on PR: [url]{pr_url}[/url]")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task(f"Executing {normalized_command}...", total=None)
            run(args=args)
        console.print(f"[success]✓ Command '{normalized_command}' completed successfully![/success]")
    except Exception as e:
        console.print(f"[error]✗ Error executing command '{normalized_command}':[/error] {str(e)}")
        logger.error(f"Error executing command '{normalized_command}': {str(e)}")
        raise


def run(inargs: Optional[List[str]] = None, args: Optional[argparse.Namespace] = None) -> Any:
    """
    Main entry point for executing PR Insight commands.

    This function handles the execution of PR Insight commands either through
    direct argument passing or via command line arguments.

    Args:
        inargs: Optional list of command-line arguments to parse
        args: Optional pre-parsed arguments (if already available)

    Returns:
        The result of the executed command or None if execution fails

    Raises:
        RuntimeError: If both PR URL and issue URL are missing
    """
    try:
        # Setup argument parser
        parser = set_parser()

        # Parse arguments if not already provided
        if not args:
            args = parser.parse_args(inargs)

        # Validate required arguments
        if not args.pr_url and not args.issue_url:
            console.print("[warning]⚠ Either PR URL or issue URL is required[/warning]")
            logger.warning("Either PR URL or issue URL is required")
            display_rich_help()
            return None

        # Normalize command to lowercase
        command = args.command.lower()
        logger.info(f"Executing command: {command}")
        console.print(f"Executing command: [command]{command}[/command]")

        # Set CLI mode in configuration
        get_settings().set(CONFIG_CLI_MODE, True)

        # Define the async execution logic
        async def inner() -> Any:
            """Execute the PR Insight command asynchronously."""
            try:
                # Create PRInsight instance
                pr_insight = PRInsight()

                # Handle either issue or PR URL
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TimeRemainingColumn(),
                    console=console
                ) as progress:
                    task_id = progress.add_task("[cyan]Processing...", total=None)

                    if args.issue_url:
                        logger.info(f"Processing issue: {args.issue_url}")
                        progress.update(task_id, description=f"[cyan]Processing issue: {args.issue_url}")
                        result = await asyncio.create_task(
                            pr_insight.handle_request(args.issue_url, [command] + args.rest)
                        )
                    else:
                        logger.info(f"Processing PR: {args.pr_url}")
                        progress.update(task_id, description=f"[cyan]Processing PR: {args.pr_url}")
                        result = await asyncio.create_task(
                            pr_insight.handle_request(args.pr_url, [command] + args.rest)
                        )

                    # Simulate some progress for visual feedback
                    progress.update(task_id, total=100)
                    for i in range(0, 101, 10):
                        if i > 0:  # Skip first iteration to show initial spinner
                            progress.update(task_id, completed=i)
                            await asyncio.sleep(0.05)

                # Wait for event queue if callbacks are enabled
                if get_settings().litellm.get("enable_callbacks", False):
                    logger.debug("Waiting for event queue to complete")
                    pending_tasks = [
                        task for task in asyncio.all_tasks()
                        if task is not asyncio.current_task()
                    ]
                    if pending_tasks:
                        await asyncio.wait(pending_tasks)

                return result
            except Exception as e:
                logger.error(f"Error during command execution: {str(e)}")
                raise

        # Run the async function
        try:
            result = asyncio.run(inner())
            if not result:
                logger.warning("Command execution returned no result")
                parser.print_help()
            return result
        except KeyboardInterrupt:
            logger.info("Operation cancelled by user")
            return None

    except Exception as e:
        logger.error(f"Unhandled exception in run: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        logger.info(f"Starting PR Insight CLI v{get_version()}")
        result = run()
        sys.exit(0 if result else 1)
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)
