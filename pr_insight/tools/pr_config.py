import logging
from dynaconf import Dynaconf
from pr_insight.config_loader import get_settings
from pr_insight.git_providers import get_git_provider

logger = logging.getLogger(__name__)

class PRConfig:
    """
    The PRConfig class is responsible for listing all configuration options available for the user.
    """
    def __init__(self, pr_url: str, args=None, ai_handler=None):
        """
        Initialize the PRConfig object with the necessary attributes and objects to comment on a pull request.

        Args:
            pr_url (str): The URL of the pull request to be reviewed.
            args (list, optional): List of arguments passed to the PRReviewer class. Defaults to None.
        """
        self.git_provider = get_git_provider()(pr_url)

    async def run(self):
        """
        Run the PRConfig process to get and publish configuration settings.

        This method retrieves the configuration settings, prepares them for display, and publishes them as a comment
        on the pull request.
        """
        try:
            logger.info('Getting configuration settings...')
            pr_comment = self._prepare_pr_configs()
            if get_settings().config.publish_output:
                logger.info('Pushing configs...')
                self.git_provider.publish_comment(pr_comment)
                self.git_provider.remove_initial_comment()
        except Exception as e:
            logger.error("Failed to run PRConfig: %s", e)
        return ""

    def _prepare_pr_configs(self) -> str:
        """
        Prepare the configuration settings for display.

        This method retrieves the configuration settings from the configuration file, filters out irrelevant settings,
        and formats them as a markdown string for display.

        Returns:
            str: The formatted configuration settings as a markdown string.
        """
        try:
            if conf_file := get_settings().find_file("configuration.toml"):
                conf_settings = Dynaconf(settings_files=[conf_file])
                configuration_headers = [header.lower() for header in conf_settings.keys()]
                relevant_configs = self._filter_relevant_configs(configuration_headers)
                markdown_text = self._format_configs_to_markdown(relevant_configs)
                logger.info("Possible Configurations outputted to PR comment", extra={"artifact": markdown_text})
                return markdown_text
        except Exception as e:
            logger.error("Error preparing PR configs: %s", e)
            return ""

    @staticmethod
    def _filter_relevant_configs(configuration_headers):
        """
        Filter relevant configuration settings.

        Args:
            configuration_headers (list): List of relevant configuration headers.

        Returns:
            dict: Filtered configuration settings.
        """
        return {
            header: configs for header, configs in get_settings().to_dict().items()
            if (header.lower().startswith("pr_") or header.lower().startswith("config")) and header.lower() in configuration_headers
        }

    @staticmethod
    def _format_configs_to_markdown(relevant_configs):
        """
        Format configuration settings to markdown.

        Args:
            relevant_configs (dict): Relevant configuration settings.

        Returns:
            str: Formatted markdown string.
        """
        skip_keys = [
            'ai_disclaimer', 'ai_disclaimer_title', 'ANALYTICS_FOLDER', 'secret_provider', "skip_keys",
            'trial_prefix_message', 'no_eligible_message', 'identity_provider', 'ALLOWED_REPOS', 'APP_NAME'
        ]
        extra_skip_keys = get_settings().config.get('config.skip_keys', [])
        if extra_skip_keys:
            skip_keys.extend(extra_skip_keys)

        markdown_text = "<details> <summary><strong>🛠️ PR-Insight Configurations:</strong></summary> \n\n"
        markdown_text += "\n\n```yaml\n\n"
        for header, configs in relevant_configs.items():
            if configs:
                markdown_text += "\n\n"
                markdown_text += f"==================== {header} ===================="
            for key, value in configs.items():
                if key not in skip_keys:
                    markdown_text += f"\n{header.lower()}.{key.lower()} = {repr(value) if isinstance(value, str) else value}  "
        markdown_text += "\n```"
        markdown_text += "\n</details>\n"
        return markdown_text
