"""Prompt loader for loading and formatting prompts from files."""

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
        self._settings = settings  # Use the global settings instance
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

        Returns:
            Profile or None: User profile if found
        """
        if self._profile is None and self.user_id:
            try:
                # Convert PydanticObjectId to regular ObjectId before passing to service
                # The service's get_profile method will handle any needed conversions
                self._profile = await self._profile_service.get_profile_by_user_id(
                    self.user_id
                )
                self.logger.debug(
                    f"Successfully loaded profile for user {self.user_id}"
                )
            except NotFoundException:
                self.logger.warning(f"No profile found for user {self.user_id}")
                # Fall back to default settings
            except ValueError as e:
                self.logger.error(f"Invalid user ID format: {e}")
            except Exception as e:
                self.logger.error(f"Error loading profile: {str(e)}")

        return self._profile

    async def _get_preference_variables(self) -> Dict[str, Any]:
        """Get variables from user profile preferences with fallbacks from settings.

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

        # If user ID is provided, try to get user-specific preferences
        profile = await self._get_profile()
        if profile and profile.preferences:
            self.logger.debug("Merging user preferences with defaults")
            preferences_dict = profile.preferences.model_dump()

            # Extract nested preferences with proper flattening for templates
            for category, values in preferences_dict.items():
                if isinstance(values, dict):
                    # Handle nested dictionaries (like career_summary_details)
                    for key, value in values.items():
                        # Add direct format
                        variables[f"{category}_{key}"] = value

                        # Special case for details dictionaries that contain min_words, max_words, etc.
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

        return variables

    async def _format_prompt(
        self, prompt_name: str, add_life_story: bool = False
    ) -> str:
        """Format a prompt with user preferences.

        Args:
            prompt_name: Name of the prompt to format
            add_life_story: Whether to add life story to variables (deprecated, kept for compatibility)

        Returns:
            Formatted prompt string

        Raises:
            KeyError: If prompt_name is not found in prompt_map
        """
        try:
            # Get prompt template
            prompt = self._prompt_map[prompt_name]

            # Return unformatted prompt if no formatting needed
            if not self.user_id and not self._settings.preferences:
                return str(prompt)

            # Get variables for formatting
            variables = await self._get_preference_variables()

            # Add extra variables specific to certain prompts
            self._add_prompt_specific_variables(prompt_name, variables)

            # Create a Template object for safe substitution (handles LaTeX content better)
            template = Template(str(prompt))

            # Use safe_substitute which doesn't raise errors for missing placeholders
            # This is much safer when dealing with LaTeX templates
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

        Args:
            prompt_name: Name of the prompt
            variables: Dictionary of variables to update
        """
        # Variables needed for the career summary prompt
        if prompt_name == "career_summary":
            if "job_titles" not in variables:
                variables["job_titles"] = '[{"title": "Software Engineer", "years": 3}]'

        # Variables needed for work experience prompt
        if prompt_name == "work_experience":
            if "bullet_points_per_job" not in variables:
                variables["bullet_points_per_job"] = variables.get(
                    "work_experience_details_bullet_points_per_job", 3
                )

        # Variables for education prompt
        if prompt_name == "education":
            if "max_courses" not in variables:
                variables["max_courses"] = variables.get(
                    "education_details_max_courses", 4
                )

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


async def test_prompt_loader():
    """Test the PromptLoader functionality with a real user profile."""
    # Configure logging for the test
    configure_logging(log_level="DEBUG")
    test_logger = get_logger("prompt_loader_test")

    test_logger.info("Starting prompt loader test")

    try:
        # Initialize database connection first
        from core.database.init import init_db

        client = await init_db()
        if not client:
            test_logger.error("Failed to initialize database connection")
            return
        test_logger.info("Successfully initialized database connection")

        # Get test user ID from settings
        settings = Settings()
        test_user_id_str = "67d713143f8ee422d6db534a"

        # Convert string ID to PydanticObjectId
        if not ObjectId.is_valid(test_user_id_str):
            test_logger.error(f"Invalid test user ID format: {test_user_id_str}")
            return

        test_user_id = PydanticObjectId(test_user_id_str)
        test_logger.info(f"Using test user ID: {test_user_id}")

        # Initialize loader with test user ID
        loader = PromptLoader(test_user_id)

        # First, check if profile was loaded
        profile = await loader._get_profile()
        if profile:
            test_logger.info(f"Profile found for user {test_user_id}")
            test_logger.info(f"Full name: {profile.full_name}")
            test_logger.info(f"Email: {profile.email}")
            test_logger.info(f"User ID in profile: {profile.user_id}")

            print(f"\nProfile found for user {test_user_id}")
            print(f"Full name: {profile.full_name}")
            print(f"Email: {profile.email}")
            print(f"User ID in profile: {profile.user_id} ({type(profile.user_id)})")
        else:
            test_logger.warning(f"No profile found for user {test_user_id}")
            print(f"\nNo profile found for user {test_user_id}")
            print("Using default settings for prompt variables")

            # Do a direct check with ProfileRepository for diagnosis
            try:
                repo = ProfileRepository()
                test_logger.debug("Trying direct repository access...")
                direct_profile = await repo.get_by_user_id(test_user_id)
                if direct_profile:
                    test_logger.info("Profile found with direct repository access")
                    print(f"However, profile found directly with repository!")
                    print(f"Profile ID: {direct_profile.id}")
                    print(
                        f"User ID in profile: {direct_profile.user_id} ({type(direct_profile.user_id)})"
                    )
                else:
                    test_logger.warning(
                        "Profile not found with direct repository access either"
                    )
                    print("Profile not found with direct repository access either.")
            except Exception as e:
                test_logger.error(f"Error in direct repository check: {e}")
                print(f"Error in direct repository check: {e}")

        # Next, show what variables are available (excluding sensitive data)
        try:
            variables = await loader._get_preference_variables()

            # Filter out potentially sensitive information
            filtered_variables = {}
            sensitive_keys = [
                "email",
                "password",
                "api_key",
                "secret",
                "token",
                "life_story",
            ]

            for key, value in variables.items():
                # Skip sensitive keys
                if any(sensitive in key.lower() for sensitive in sensitive_keys):
                    filtered_variables[key] = "[REDACTED]"
                else:
                    filtered_variables[key] = value

            print(f"\nAvailable variables for formatting ({len(filtered_variables)}):")
            print("-" * 50)
            for key, value in sorted(filtered_variables.items()):
                print(f"{key}: {value}")
            print("-" * 50)
        except Exception as e:
            test_logger.error(f"Error getting variables: {e}")
            print(f"Error getting variables: {e}")

        try:
            # Get the complete formatted prompt
            prompt_name = "folder_name"
            prompt = await loader.get_section_prompt(prompt_name)

            # Print the formatted prompt with clear separation
            print(f"\n{'=' * 80}")
            print(f"COMPLETE {prompt_name.upper()} PROMPT WITH FILLED PLACEHOLDERS:")
            print(f"{'=' * 80}")
            # Print with line breaks for readability
            for line in prompt.split("\n"):
                print(line)
            print(f"{'=' * 80}")
            test_logger.info(f"Successfully loaded and formatted {prompt_name} prompt")

        except Exception as e:
            import traceback

            test_logger.error(f"Failed to load {prompt_name} prompt: {e}")
            print(f"\nError loading prompt: {e}")
            traceback.print_exc()

            # Fallback to unformatted prompt
            print("\nFalling back to unformatted prompt:")
            try:
                unformatted = str(loader._prompt_map[prompt_name])
                # Print with line breaks for readability
                for line in unformatted.split("\n"):
                    print(line)
            except Exception as nested_e:
                test_logger.error(f"Could not display unformatted prompt: {nested_e}")
                print(f"Could not display unformatted prompt: {nested_e}")

    except Exception as e:
        import traceback

        test_logger.error(f"Test failed: {e}")
        print(f"Test failed: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    import asyncio

    print("\n" + "=" * 80)
    print(" PROMPT LOADER TEST ".center(80, "="))
    print("=" * 80 + "\n")

    try:
        asyncio.run(test_prompt_loader())
        print("\n" + "=" * 80)
        print(" TEST COMPLETED ".center(80, "="))
        print("=" * 80 + "\n")
    except Exception as e:
        import traceback

        print("\n" + "=" * 80)
        print(" TEST FAILED ".center(80, "="))
        print("-" * 80)
        print(f"Error: {e}")
        traceback.print_exc()
        print("=" * 80 + "\n")
        sys.exit(1)
