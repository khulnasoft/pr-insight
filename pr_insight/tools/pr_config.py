import logging
from dynaconf import Dynaconf
from pr_insight.config_loader import get_settings
from pr_insight.git_providers import get_git_provider
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class PRConfig:
    """
    The PRConfig class is responsible for listing all configuration options available for the user.
    It retrieves, filters and formats configuration settings from a configuration file and can publish
    them as a comment on a pull request.
    """
    def __init__(self, pr_url: str, args: Optional[List] = None, ai_handler=None):
        """
        Initialize the PRConfig object with the necessary attributes and objects to comment on a pull request.

        Args:
            pr_url (str): The URL of the pull request to be reviewed.
            args (Optional[List]): List of arguments passed to the PRReviewer class. Defaults to None.
            ai_handler: AI handler instance. Currently unused.
        """
        self.git_provider = get_git_provider()(pr_url)

    async def run(self) -> str:
        """
        Run the PRConfig process to get and publish configuration settings.

        This method retrieves the configuration settings, prepares them for display, and optionally
        publishes them as a comment on the pull request.

        Returns:
            str: Empty string, maintained for compatibility.

        Raises:
            Exception: Logs any errors that occur during execution but doesn't re-raise.
        """
        try:
            logger.info('Getting configuration settings...')
            pr_comment = self._prepare_pr_configs()
            if pr_comment and get_settings().config.publish_output:
                logger.info('Publishing configs to pull request...')
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
            str: The formatted configuration settings as a markdown string. Returns empty string if an error occurs.
        """
        try:
            conf_file = get_settings().find_file("configuration.toml")
            if not conf_file:
                logger.warning("No configuration.toml file found")
                return ""
                
            conf_settings = Dynaconf(settings_files=[conf_file])
            configuration_headers = [header.lower() for header in conf_settings.keys()]
            relevant_configs = self._filter_relevant_configs(configuration_headers)
            
            if not relevant_configs:
                logger.info("No relevant configurations found")
                return ""
                
            markdown_text = self._format_configs_to_markdown(relevant_configs)
            logger.info("Configuration settings prepared successfully", extra={"artifact": markdown_text})
            return markdown_text
            
        except Exception as e:
            logger.error("Error preparing PR configs: %s", e)
            return ""

    @staticmethod
    def _filter_relevant_configs(configuration_headers: List[str]) -> Dict:
        """
        Filter relevant configuration settings based on prefixes and headers.

        Args:
            configuration_headers (List[str]): List of configuration headers from the config file.

        Returns:
            Dict: Filtered configuration settings that start with 'pr_' or 'config' and exist in headers.
        """
        settings_dict = get_settings().to_dict()
        return {
            header: configs for header, configs in settings_dict.items()
            if (header.lower().startswith(("pr_", "config"))) and header.lower() in configuration_headers
        }

    @staticmethod
    def _format_configs_to_markdown(relevant_configs: Dict) -> str:
        """
        Format configuration settings to markdown with proper formatting and structure.

        Args:
            relevant_configs (Dict): Dictionary of relevant configuration settings to format.

        Returns:
            str: Formatted markdown string with configuration details in a collapsible section.
        """
        skip_keys = {
            'ai_disclaimer', 'ai_disclaimer_title', 'ANALYTICS_FOLDER', 'secret_provider', 
            'skip_keys', 'trial_prefix_message', 'no_eligible_message', 'identity_provider', 
            'ALLOWED_REPOS', 'APP_NAME'
        }
        
        extra_skip_keys = get_settings().config.get('config.skip_keys', [])
        skip_keys.update(extra_skip_keys)

        markdown_text = "<details> <summary><strong>🛠️ PR-Insight Configurations:</strong></summary>\n\n"
        markdown_text += "```yaml\n"
        
        for header, configs in relevant_configs.items():
            if not configs:
                continue
                
            markdown_text += f"\n==================== {header} ====================\n"
            for key, value in configs.items():
                if key not in skip_keys:
                    formatted_value = repr(value) if isinstance(value, str) else value
                    markdown_text += f"{header.lower()}.{key.lower()} = {formatted_value}\n"
                    
        markdown_text += "```\n</details>\n"
        return markdown_text
