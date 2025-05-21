"""Prompt loader for loading and accessing prompt templates.

This module provides functionality to load prompt templates from files.
It focuses on retrieval operations, not on format or transformation logic.
"""

from typing import List

from config.logging_config import configure_logging, get_logger
from config.settings import Settings
from prompts import (
    COVER_LETTER_PROMPT,
    FOLDER_NAME_PROMPT,
    RESUME_PROMPT,
    SYSTEM_PROMPT,
)

# Initialize global settings and logging
settings = Settings()
configure_logging()
logger = get_logger(__name__)


class PromptLoader:
    """A class to load and access prompt templates.

    This loader accesses file-based prompts from the prompts directory
    and provides methods to retrieve them.
    """

    def __init__(self):
        """Initialize the PromptLoader."""
        self.logger = get_logger(self.__class__.__name__)

        # Map prompt names to prompt instances
        self._prompt_map = {
            "cover_letter": COVER_LETTER_PROMPT,
            "folder_name": FOLDER_NAME_PROMPT,
            "resume": RESUME_PROMPT,
            "system": SYSTEM_PROMPT,
        }
        self.logger.debug(
            f"PromptLoader initialized with {len(self._prompt_map)} prompts"
        )

    def get_prompt_template(self, prompt_name: str):
        """Get a prompt template object by name.

        Args:
            prompt_name: Name of the prompt template to retrieve

        Returns:
            BasePrompt: The prompt template object

        Raises:
            KeyError: If prompt_name is not found in prompt_map
        """
        prompt = self._prompt_map.get(prompt_name.lower())
        if not prompt:
            self.logger.error(f"Prompt template not found: {prompt_name}")
            raise KeyError(f"Prompt template not found: {prompt_name}")
        return prompt

    def get_prompt_text(self, prompt_name: str) -> str:
        """Get the unformatted prompt text.

        Args:
            prompt_name: Name of the prompt to retrieve

        Returns:
            str: The unformatted prompt template text

        Raises:
            KeyError: If prompt_name is not found in prompt_map
        """
        try:
            return str(self.get_prompt_template(prompt_name))
        except KeyError:
            self.logger.error(f"Prompt not found: {prompt_name}")
            raise

    def get_all_prompt_names(self) -> List[str]:
        """Get a list of all available prompt names.

        Returns:
            List[str]: List of all prompt names that can be loaded
        """
        return list(self._prompt_map.keys())
