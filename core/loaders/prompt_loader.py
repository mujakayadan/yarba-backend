"""Prompt loader for loading and formatting prompts from files.

This module provides functionality to load prompt templates and format them
with user-specific preferences. It handles database access to retrieve user
profiles and properly formats prompts with appropriate substitutions.
"""

import os
import sys
from pathlib import Path
from string import Template
from typing import Any, Dict, List, Optional

# Add project root to Python path when running as script
if __name__ == "__main__":
    project_root = str(Path(__file__).parent.parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    print(f"Added {project_root} to Python path")
    print(f"Python path: {sys.path}")

from beanie import PydanticObjectId
from bson import ObjectId
from bson.errors import InvalidId

from config.logging_config import configure_logging, get_logger
from config.settings import Settings
from core.exceptions.base import NotFoundException
from core.repositories.profile_repository import ProfileRepository
from core.repositories.user_repository import UserRepository
from core.services.profile_service import ProfileService
from prompts import *

# Initialize global settings and logging
settings = Settings()
configure_logging()
logger = get_logger(__name__)


class PromptLoader:
    """A class to load and format prompts with user preferences.

    This loader accesses file-based prompts from the prompts directory
    and formats them with user preferences and fallback values from settings.
    """

    def __init__(self, user_id: Optional[PydanticObjectId] = None):
        """Initialize the PromptLoader with a user_id.

        Args:
            user_id: Optional user ID as PydanticObjectId
        """
        self.user_id = user_id
        self._profile = None
        self._profile_service = ProfileService(ProfileRepository(), UserRepository())
        self._settings = settings
        self.logger = get_logger(self.__class__.__name__)

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
            f"PromptLoader initialized with {len(self._prompt_map)} prompts"
        )

    async def _get_profile(self):
        """Get user profile using the profile service.

        Fetches the user profile based on user_id and caches the result for
        subsequent calls.

        Returns:
            Profile or None: User profile if found
        """
        if self._profile is None and self.user_id:
            try:
                self._profile = await self._profile_service.get_profile_by_user_id(
                    self.user_id
                )
                self.logger.debug(
                    f"Successfully loaded profile for user {self.user_id}"
                )
            except NotFoundException:
                self.logger.warning(f"No profile found for user {self.user_id}")
            except ValueError as e:
                self.logger.error(f"Invalid user ID format: {e}")
            except Exception as e:
                self.logger.error(f"Error loading profile: {str(e)}")

        return self._profile

    async def _get_preference_variables(self) -> Dict[str, Any]:
        """Get variables from user profile preferences with fallbacks from settings.

        First loads default settings, then overrides with user-specific preferences
        if available. Handles nested preferences by flattening them for template use.

        Returns:
            Dictionary of variables for template substitution
        """
        # Get default preferences from settings
        variables = self._settings.preferences.get_prompt_variables()
        self.logger.debug(
            f"Loaded {len(variables)} default preference variables from settings"
        )

        # Add default for life story
        variables["life_story"] = "No personal story available."

        # Load user profile and merge preferences if available
        profile = await self._get_profile()
        if profile and profile.preferences:
            self._merge_profile_preferences(profile, variables)

        return variables

    def _merge_profile_preferences(self, profile, variables: Dict[str, Any]) -> None:
        """Merge profile preferences into the variables dictionary.

        Args:
            profile: User profile with preferences
            variables: Dictionary to update with profile preferences
        """
        self.logger.debug("Merging user preferences with defaults")
        preferences_dict = profile.preferences.model_dump()

        # Extract nested preferences with proper flattening
        for category, values in preferences_dict.items():
            if isinstance(values, dict):
                # Handle nested dictionaries (like career_summary_details)
                for key, value in values.items():
                    # Add direct format
                    variables[f"{category}_{key}"] = value

                    # Special case for details dictionaries
                    if category.endswith("_details") and isinstance(
                        value, (int, str, float, bool)
                    ):
                        section_name = category.replace("_details", "")
                        variables[f"{section_name}_details_{key}"] = value
            else:
                variables[category] = values

        # Add other profile fields that might be needed
        if hasattr(profile, "life_story") and profile.life_story:
            variables["life_story"] = profile.life_story

        self.logger.debug(f"Final variable count after merging: {len(variables)}")

    async def _format_prompt(self, prompt_name: str) -> str:
        """Format a prompt with user preferences.

        Args:
            prompt_name: Name of the prompt to format

        Returns:
            Formatted prompt string

        Raises:
            KeyError: If prompt_name is not found in prompt_map
            Exception: If any other error occurs during formatting
        """
        try:
            # Get prompt template
            prompt = self._prompt_map[prompt_name]

            # Return unformatted prompt if no formatting needed
            if not self.user_id and not self._settings.preferences:
                return str(prompt)

            # Get variables and add prompt-specific ones
            variables = await self._get_preference_variables()
            self._add_prompt_specific_variables(prompt_name, variables)

            # Create and use template for safe substitution
            template = Template(str(prompt))
            return template.safe_substitute(variables)

        except KeyError:
            self.logger.error(f"Prompt not found: {prompt_name}")
            raise
        except Exception as e:
            self.logger.error(f"Error formatting prompt: {e}")
            raise

    def _add_prompt_specific_variables(
        self, prompt_name: str, variables: Dict[str, Any]
    ) -> None:
        """Add additional variables needed for specific prompts.

        Sets default values for variables required by specific prompts
        when they aren't provided in the user preferences.

        Args:
            prompt_name: Name of the prompt
            variables: Dictionary of variables to update
        """
        # Career summary prompt defaults
        if prompt_name == "career_summary" and "job_titles" not in variables:
            variables["job_titles"] = '[{"title": "Software Engineer", "years": 3}]'

        # Work experience prompt defaults
        if (
            prompt_name == "work_experience"
            and "bullet_points_per_job" not in variables
        ):
            variables["bullet_points_per_job"] = variables.get(
                "work_experience_details_bullet_points_per_job", 3
            )

        # Education prompt defaults
        if prompt_name == "education" and "max_courses" not in variables:
            variables["max_courses"] = variables.get("education_details_max_courses", 4)

    async def get_section_prompt(self, section: str) -> str:
        """Get the prompt for a specific section with user preferences.

        Args:
            section: The section name (e.g. 'career_summary', 'skills')

        Returns:
            str: The formatted prompt text

        Raises:
            KeyError: If section prompt doesn't exist
        """
        return await self._format_prompt(section.lower())

    async def get_system_prompt(self) -> str:
        """Get the system prompt."""
        return await self._format_prompt("system")

    async def get_folder_name_prompt(self) -> str:
        """Get the folder name prompt."""
        return await self._format_prompt("folder_name")

    async def get_cover_letter_prompt(self) -> str:
        """Get the cover letter prompt with user's life story.

        Returns:
            str: The cover letter prompt with user's life story
        """
        return await self._format_prompt("cover_letter")

    def refresh_profile(self) -> None:
        """Force reload of user profile."""
        self._profile = None
        self.logger.debug("User profile cache cleared")

    async def get_all_prompt_names(self) -> List[str]:
        """Get a list of all available prompt names.

        Returns:
            List[str]: List of all prompt names that can be loaded
        """
        return list(self._prompt_map.keys())
