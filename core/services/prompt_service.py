"""Prompt service for loading and managing prompts."""

import importlib
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Add project root to Python path when running as script
if __name__ == "__main__":
    project_root = str(Path(__file__).parent.parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from beanie import PydanticObjectId

from config.logging_config import get_logger
from config.settings import settings
from core.exceptions.base import NotFoundException
from core.repositories.user_repository import UserRepository

logger = get_logger(__name__)


class PromptService:
    """Service for prompt operations."""

    def __init__(
        self,
        user_repository: Optional[UserRepository] = None,
        user_id: Optional[Union[str, PydanticObjectId]] = None,
    ):
        """
        Initialize the prompt service.

        Args:
            user_repository: User repository for personalized prompts
            user_id: User ID for personalized prompts
        """
        self.prompts_dir = "prompts"  # The Python module where prompts are stored
        self.user_repository = user_repository
        self.user_id = user_id
        self.logger = get_logger(self.__class__.__name__)
        logger.debug(f"Initialized PromptService with user_id: {user_id}")

    async def _get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
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

    async def _load_prompt_module(self, module_name: str):
        """
        Load a prompt module dynamically.

        Args:
            module_name: Name of the module to load

        Returns:
            The loaded prompt object

        Raises:
            NotFoundException: If the module doesn't exist
        """
        try:
            # Import the module dynamically
            module_path = f"{self.prompts_dir}.{module_name}"
            module = importlib.import_module(module_path)

            # Try to get the specific prompt constant (highest priority)
            specific_constant_name = f"{module_name.upper()}_PROMPT"
            if hasattr(module, specific_constant_name):
                prompt_obj = getattr(module, specific_constant_name)
                # Check for template attribute (_template or template)
                if hasattr(prompt_obj, "_template"):
                    return prompt_obj._template
                elif hasattr(prompt_obj, "template"):
                    return prompt_obj.template

            # Try to find the class instance
            class_name = (
                "".join(word.capitalize() for word in module_name.split("_")) + "Prompt"
            )
            if hasattr(module, class_name):
                prompt_class = getattr(module, class_name)
                # Check if it's a class or instance
                if isinstance(prompt_class, type):
                    # It's a class, instantiate it
                    prompt_obj = prompt_class()
                else:
                    # It's already an instance
                    prompt_obj = prompt_class

                # Check for template attribute (_template or template)
                if hasattr(prompt_obj, "_template"):
                    return prompt_obj._template
                elif hasattr(prompt_obj, "template"):
                    return prompt_obj.template

            # Try to get the TEMPLATE constant directly
            if hasattr(module, "TEMPLATE"):
                return module.TEMPLATE

            self.logger.error(
                f"Could not find valid prompt template in module: {module_path}"
            )
            raise NotFoundException(f"Prompt not found in module: {module_path}")
        except ImportError as e:
            self.logger.error(f"Could not import prompt module {module_name}: {e}")
            raise NotFoundException(f"Prompt module not found: {module_name}")

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
            prompt_obj = await self._load_prompt_module(f"{section.lower()}_prompt")
            return prompt_obj.template
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
        try:
            prompt_obj = await self._load_prompt_module("system_prompt")
            return prompt_obj.template
        except Exception as e:
            self.logger.error(f"Error loading system prompt: {e}")
            raise

    async def get_folder_name_prompt(self) -> str:
        """
        Get the folder name prompt.

        Returns:
            str: The folder name prompt text

        Raises:
            NotFoundException: If the prompt doesn't exist
        """
        try:
            prompt_obj = await self._load_prompt_module("folder_name_prompt")
            return prompt_obj.template
        except Exception as e:
            self.logger.error(f"Error loading folder name prompt: {e}")
            raise

    async def get_cover_letter_prompt(self) -> str:
        """
        Get the cover letter prompt.

        Returns:
            str: The cover letter prompt

        Raises:
            NotFoundException: If the prompt doesn't exist
        """
        try:
            prompt_obj = await self._load_prompt_module("cover_letter_prompt")
            return prompt_obj.template
        except Exception as e:
            self.logger.error(f"Error loading cover letter prompt: {e}")
            raise

    async def get_available_prompts(self) -> List[str]:
        """
        Get a list of all available prompts.

        Returns:
            List of prompt names that can be accessed
        """
        try:
            # This would need filesystem access to enumerate the prompts
            # For now, return a hardcoded list of known prompts
            return [
                "system",
                "folder_name",
                "cover_letter",
                "career_summary",
                "skills",
                "work_experience",
                "education",
                "projects",
            ]
        except Exception as e:
            self.logger.error(f"Error getting available prompts: {e}")
            return []

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
                if name == "cover_letter":
                    result[name] = await self.get_cover_letter_prompt()
                elif name == "system":
                    result[name] = await self.get_system_prompt()
                elif name == "folder_name":
                    result[name] = await self.get_folder_name_prompt()
                else:
                    result[name] = await self.get_section_prompt(name)
            except Exception as e:
                self.logger.warning(f"Failed to load prompt '{name}': {e}")
                result[name] = f"Error: {str(e)}"
        return result

    def set_user_id(self, user_id: Optional[Union[str, PydanticObjectId]]) -> None:
        """
        Set or change the user ID for personalized prompts.

        Args:
            user_id: User ID to set
        """
        self.user_id = user_id
        self.logger.debug(f"User changed to: {user_id}")
