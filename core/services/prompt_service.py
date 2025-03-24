"""Prompt service for loading and managing prompts."""

import logging
from typing import Any, Dict, List, Optional

from beanie import PydanticObjectId

from config.logging_config import get_logger
from config.settings import settings
from core.exceptions.base import NotFoundException
from core.repositories.user_repository import UserRepository
from prompts import *  # Import all prompts directly

logger = get_logger(__name__)


class PromptService:
    """Service for prompt operations."""

    def __init__(
        self,
        user_repository: Optional[UserRepository] = None,
        user_id: Optional[PydanticObjectId] = None,
    ):
        """
        Initialize the prompt service.

        Args:
            user_repository: User repository for personalized prompts
            user_id: User ID for personalized prompts
        """
        self.user_repository: Optional[UserRepository] = user_repository
        self.user_id: Optional[PydanticObjectId] = user_id
        self.logger = get_logger(self.__class__.__name__)
        logger.debug(f"Initialized PromptService with user_id: {user_id}")

        # Map section names to prompt instances
        self._prompt_map = {
            "awards": AWARDS_PROMPT,
            "career_summary": CAREER_SUMMARY_PROMPT,
            "cover_letter": COVER_LETTER_PROMPT,
            "education": EDUCATION_PROMPT,
            "folder_name": FOLDER_NAME_PROMPT,
            "header": HEADER_PROMPT,
            "job_titles": JOB_TITLES_PROMPT,
            "personal_information": PERSONAL_INFORMATION_PROMPT,
            "projects": PROJECTS_PROMPT,
            "publications": PUBLICATIONS_PROMPT,
            "skills": SKILLS_PROMPT,
            "system": SYSTEM_PROMPT,
            "work_experience": WORK_EXPERIENCE_PROMPT,
        }
        self.logger.debug(
            f"PromptService initialized with {len(self._prompt_map)} prompts"
        )

    async def _get_user_preferences(
        self, user_id: PydanticObjectId
    ) -> Optional[Dict[str, Any]]:
        """
        Get user preferences using the repository.

        Args:
            user_id: User ID

        Returns:
            Optional[Dict[str, Any]]: User preferences if found, None otherwise
        """
        if not self.user_repository:
            self.logger.warning(
                "User repository not provided, cannot fetch preferences"
            )
            return None

        profile = await self.user_repository.get_by_user_id(user_id)
        if profile and profile.preferences:
            self.logger.debug(f"Loaded preferences for user {user_id}")
            return profile.preferences.model_dump()

        self.logger.debug(f"No preferences found for user {user_id}")
        return None

    async def get_section_prompt(self, section: str) -> str:
        """
        Get the prompt for a specific section.

        Args:
            section: The section name (e.g. 'career_summary', 'skills')

        Returns:
            str: The prompt text

        Raises:
            NotFoundException: If the prompt doesn't exist
        """
        try:
            prompt = self._prompt_map.get(section.lower())
            if not prompt:
                self.logger.error(f"Prompt not found: {section}")
                raise NotFoundException(f"Prompt not found: {section}")
            return str(prompt)
        except Exception as e:
            self.logger.error(f"Error loading section prompt '{section}': {e}")
            raise

    async def get_system_prompt(self) -> str:
        """
        Get the system prompt.

        Returns:
            str: The system prompt text

        Raises:
            NotFoundException: If the prompt doesn't exist
        """
        return await self.get_section_prompt("system")

    async def get_folder_name_prompt(self) -> str:
        """
        Get the folder name prompt.

        Returns:
            str: The folder name prompt text

        Raises:
            NotFoundException: If the prompt doesn't exist
        """
        return await self.get_section_prompt("folder_name")

    async def get_cover_letter_prompt(self) -> str:
        """
        Get the cover letter prompt.

        Returns:
            str: The cover letter prompt

        Raises:
            NotFoundException: If the prompt doesn't exist
        """
        return await self.get_section_prompt("cover_letter")

    async def get_available_prompts(self) -> List[str]:
        """
        Get a list of all available prompts.

        Returns:
            List of prompt names that can be accessed
        """
        return list(self._prompt_map.keys())

    async def get_multiple_prompts(self, names: List[str]) -> Dict[str, str]:
        """
        Get multiple prompts by name.

        Args:
            names: List of prompt names to retrieve

        Returns:
            Dictionary mapping prompt names to their text
        """
        result = {}
        for name in names:
            try:
                result[name] = await self.get_section_prompt(name)
            except Exception as e:
                self.logger.warning(f"Failed to load prompt '{name}': {e}")
                result[name] = f"Error: {str(e)}"
        return result

    def set_user_id(self, user_id: Optional[PydanticObjectId]) -> None:
        """
        Set or change the user ID for personalized prompts.

        Args:
            user_id: User ID to set
        """
        self.user_id = user_id
        self.logger.debug(f"User changed to: {user_id}")
