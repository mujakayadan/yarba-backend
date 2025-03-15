"""Prompt service for loading and managing prompts."""

import logging
from pathlib import Path
from string import Template
from typing import Any, Dict, Optional

from ..exceptions.base import NotFoundException
from ..models.user import User
from ..repositories.user import UserRepository
from .config import settings

logger = logging.getLogger(__name__)


class PromptService:
    """Service for loading and managing prompts for LLM operations."""

    def __init__(self, user_repository: UserRepository):
        """
        Initialize the prompt service.

        Args:
            user_repository: User repository instance
        """
        self.prompt_dir = Path(settings.paths.prompts_dir)
        self.user_repository = user_repository
        self.logger = logging.getLogger(self.__class__.__name__)

    async def _get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user preferences.

        Args:
            user_id: User ID

        Returns:
            Optional[Dict[str, Any]]: User preferences if found, None otherwise
        """
        user = await self.user_repository.get_by_id(user_id)
        if user and user.preferences:
            self.logger.debug(f"Loaded preferences for user {user_id}")
            return user.preferences

        self.logger.debug(f"No preferences found for user {user_id}")
        return None

    def _read_template_file(self, filename: str) -> Template:
        """
        Read and create a template from a file.

        Args:
            filename: Name of the file to read

        Returns:
            Template: Template object created from file contents

        Raises:
            NotFoundException: If the file doesn't exist
        """
        prompt_path = self.prompt_dir / filename
        if not prompt_path.exists():
            self.logger.error(f"Prompt file not found at {prompt_path}")
            raise NotFoundException(f"Prompt file not found: {filename}")

        with open(prompt_path, "r", encoding="utf-8") as f:
            return Template(f.read().strip())

    def _get_preference_variables(
        self, preferences: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Get variables from user preferences.

        Args:
            preferences: User preferences

        Returns:
            Dict[str, Any]: Dictionary of variables for template substitution
        """
        variables = {}
        if preferences:
            for category, values in preferences.items():
                if isinstance(values, dict):
                    for key, value in values.items():
                        variables[f"{category}_{key}"] = value
                else:
                    variables[category] = values

        return variables

    async def _add_life_story(self, variables: Dict[str, Any], user_id: str) -> None:
        """
        Add life story to variables if available.

        Args:
            variables: Dictionary to add life story to
            user_id: User ID
        """
        user = await self.user_repository.get_by_id(user_id)
        if user and user.life_story:
            variables["life_story"] = user.life_story
        else:
            variables["life_story"] = "No personal story available."

    async def load_prompt(self, filename: str, user_id: Optional[str] = None) -> str:
        """
        Load and format a prompt file with user preferences if available.

        Args:
            filename: The name of the file to load
            user_id: Optional user ID for personalization

        Returns:
            str: Formatted prompt string

        Raises:
            NotFoundException: If prompt file doesn't exist
        """
        try:
            template = self._read_template_file(filename)
            variables = {}

            if user_id:
                preferences = await self._get_user_preferences(user_id)
                variables = self._get_preference_variables(preferences)

                # Add life story if loading cover letter prompt
                if filename == "cover_letter_prompt.txt":
                    await self._add_life_story(variables, user_id)

            return template.safe_substitute(variables)

        except Exception as e:
            self.logger.error(f"Error loading prompt {filename}: {e}")
            raise

    async def get_section_prompt(
        self, section: str, user_id: Optional[str] = None
    ) -> str:
        """
        Get the prompt for a specific section with user preferences.

        Args:
            section: The section name (e.g. 'career_summary', 'skills')
            user_id: Optional user ID for personalization

        Returns:
            str: The formatted prompt text

        Raises:
            NotFoundException: If prompt file doesn't exist
        """
        filename = f"{section.lower()}_prompt.txt"
        return await self.load_prompt(filename, user_id)

    async def get_system_prompt(self, user_id: Optional[str] = None) -> str:
        """
        Get the system prompt with user preferences.

        Args:
            user_id: Optional user ID for personalization

        Returns:
            str: The formatted system prompt

        Raises:
            NotFoundException: If prompt file doesn't exist
        """
        return await self.load_prompt("system_prompt.txt", user_id)

    async def get_folder_name_prompt(self, user_id: Optional[str] = None) -> str:
        """
        Get the folder name prompt with user preferences.

        Args:
            user_id: Optional user ID for personalization

        Returns:
            str: The formatted folder name prompt

        Raises:
            NotFoundException: If prompt file doesn't exist
        """
        return await self.load_prompt("folder_name_prompt.txt", user_id)

    async def get_cover_letter_prompt(self, user_id: Optional[str] = None) -> str:
        """
        Get the cover letter prompt with user's life story.

        Args:
            user_id: Optional user ID for personalization

        Returns:
            str: The cover letter prompt with user's life story

        Raises:
            NotFoundException: If prompt file doesn't exist
        """
        return await self.load_prompt("cover_letter_prompt.txt", user_id)
