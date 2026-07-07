"""Prompt service for loading and managing prompts.

This service is responsible for retrieving prompt templates, mapping profile preferences
to template variables, and formatting prompts with those variables.
"""

from typing import Any, cast

from beanie import PydanticObjectId

from config.logging_config import get_logger
from config.settings import Settings
from core.exceptions.base import NotFoundException
from core.loaders.prompt_loader import PromptLoader
from core.repositories.profile_repository import ProfileRepository
from core.repositories.user_repository import UserRepository

logger = get_logger(__name__)


class PromptService:
    """Service for prompt operations and transformations."""

    def __init__(
        self,
        user_repository: UserRepository | None = None,
        profile_repository: ProfileRepository | None = None,
        user_id: PydanticObjectId | None = None,
    ):
        """Initialize the prompt service.

        Args:
            user_repository: User repository for personalized prompts
            profile_repository: Profile repository for user profiles
            user_id: User ID for personalized prompts
        """
        self.user_repository = user_repository if user_repository else UserRepository()
        self.profile_repository = (
            profile_repository if profile_repository else ProfileRepository()
        )
        self.user_id = user_id
        self.logger = get_logger(self.__class__.__name__)
        self.prompt_loader = PromptLoader()
        self.settings = Settings()
        self._profile = None
        self.logger.debug(f"Initialized PromptService with user_id: {user_id}")

    async def _get_profile(self):
        """Get user profile using the repositories.

        Fetches the user profile based on user_id and caches the result for
        subsequent calls.

        Returns:
            Profile or None: User profile if found
        """
        if self._profile is None and self.user_id:
            try:
                # First try to get profile directly
                self._profile = await self.profile_repository.get_by_user_id(
                    self.user_id
                )
                if not self._profile:
                    # If not found, check if user exists
                    user = await self.user_repository.get_by_id(self.user_id)
                    if user:
                        self.logger.debug(
                            f"User found but no profile exists for {self.user_id}"
                        )
                    else:
                        self.logger.warning(f"User {self.user_id} not found")
                else:
                    self.logger.debug(
                        f"Successfully loaded profile for user {self.user_id}"
                    )
            except Exception as e:
                self.logger.error(f"Error loading profile: {str(e)}")

        return self._profile

    async def _get_prompt_variables(self) -> dict[str, Any]:
        """Get variables from user profile prompt_preferences with fallbacks from settings.

        Returns:
            Dictionary of variables for template substitution
        """
        variables = {"preferences": {}, "life_story": "No personal story available."}

        try:
            # First try to get preferences directly from profile
            profile = await self._get_profile()

            if (
                profile
                and hasattr(profile, "prompt_preferences")
                and profile.prompt_preferences
            ):
                # Use preferences from profile
                self.logger.debug("Using preferences from user profile")
                variables["preferences"] = profile.prompt_preferences.model_dump()

                # Add life story if available
                if hasattr(profile, "life_story") and profile.life_story:
                    variables["life_story"] = profile.life_story
            else:
                # Fall back to default settings
                self.logger.debug(
                    "No profile preferences found, using settings fallback values"
                )
                variables["preferences"] = (
                    self.settings.preferences.get_prompt_variables()
                )
        except Exception as e:
            # Log the error and fall back to settings
            self.logger.error(f"Error loading profile preferences: {e}")
            self.logger.debug("Using settings fallback values due to error")
            variables["preferences"] = self.settings.preferences.get_prompt_variables()

        return variables

    async def get_prompt_template(self, prompt_name: str):
        """Get the prompt template object by name.

        Args:
            prompt_name: Name of the prompt template

        Returns:
            BasePrompt: The prompt template object

        Raises:
            NotFoundException: If the prompt doesn't exist
        """
        try:
            return self.prompt_loader.get_prompt_template(prompt_name.lower())
        except KeyError:
            self.logger.error(f"Prompt not found: {prompt_name}")
            raise NotFoundException(f"Prompt not found: {prompt_name}")

    async def get_prompt_text(self, prompt_name: str) -> str:
        """Get the unformatted prompt text.

        Args:
            prompt_name: Name of the prompt

        Returns:
            str: The unformatted prompt text

        Raises:
            NotFoundException: If the prompt doesn't exist
        """
        try:
            return self.prompt_loader.get_prompt_text(prompt_name.lower())
        except KeyError:
            self.logger.error(f"Prompt not found: {prompt_name}")
            raise NotFoundException(f"Prompt not found: {prompt_name}")

    async def get_prompt(self, prompt_name: str) -> str:
        """Get a formatted prompt with user preferences.

        Args:
            prompt_name: Name of the prompt (e.g. 'resume', 'cover_letter')

        Returns:
            str: The formatted prompt text

        Raises:
            NotFoundException: If the prompt doesn't exist
        """
        try:
            # Get prompt template
            prompt_template = await self.get_prompt_template(prompt_name)

            # Get variables and format using the template's format method
            variables = await self._get_prompt_variables()
            return cast(str, prompt_template.format(**variables))
        except NotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error formatting prompt '{prompt_name}': {e}")
            raise

    async def format_prompt(self, prompt_name: str, variables: dict[str, Any]) -> str:
        """Format a prompt with provided variables.

        Args:
            prompt_name: The prompt name (e.g. 'resume', 'cover_letter')
            variables: Variables to use for formatting

        Returns:
            str: The formatted prompt text

        Raises:
            NotFoundException: If the prompt doesn't exist
        """
        try:
            prompt_template = await self.get_prompt_template(prompt_name)
            return cast(str, prompt_template.format(**variables))
        except NotFoundException:
            raise
        except Exception as e:
            self.logger.error(f"Error formatting prompt '{prompt_name}': {e}")
            raise

    async def get_system_prompt(self) -> str:
        """Get the system prompt.

        Returns:
            str: The system prompt text

        Raises:
            NotFoundException: If the prompt doesn't exist
        """
        return await self.get_prompt("system")

    async def get_folder_name_prompt(self) -> str:
        """Get the folder name prompt.

        Returns:
            str: The folder name prompt text

        Raises:
            NotFoundException: If the prompt doesn't exist
        """
        return await self.get_prompt("folder_name")

    async def get_cover_letter_prompt(self) -> str:
        """Get the cover letter prompt.

        Returns:
            str: The cover letter prompt

        Raises:
            NotFoundException: If the prompt doesn't exist
        """
        return await self.get_prompt("cover_letter")

    async def get_resume_prompt(self) -> str:
        """Get the resume prompt.

        Returns:
            str: The resume prompt

        Raises:
            NotFoundException: If the prompt doesn't exist
        """
        return await self.get_prompt("resume")

    async def get_available_prompts(self) -> list[str]:
        """Get a list of all available prompts.

        Returns:
            List of prompt names that can be accessed
        """
        return self.prompt_loader.get_all_prompt_names()

    async def get_multiple_prompts(self, names: list[str]) -> dict[str, str]:
        """Get multiple prompts by name.

        Args:
            names: List of prompt names to retrieve

        Returns:
            Dictionary mapping prompt names to their text
        """
        result = {}
        for name in names:
            try:
                result[name] = await self.get_prompt(name)
            except Exception as e:
                self.logger.warning(f"Failed to load prompt '{name}': {e}")
                result[name] = f"Error: {str(e)}"
        return result

    def set_user_id(self, user_id: PydanticObjectId | None) -> None:
        """Set or change the user ID for personalized prompts.

        Args:
            user_id: User ID to set
        """
        self.user_id = user_id
        self._profile = None  # Clear cached profile
        self.logger.debug(f"User changed to: {user_id}")

    def refresh_profile(self) -> None:
        """Force reload of user profile."""
        self._profile = None
        self.logger.debug("User profile cache cleared")
