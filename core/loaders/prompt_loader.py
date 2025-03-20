"""Prompt loader for loading and formatting prompts from files."""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to Python path when running as script
if __name__ == "__main__":
    project_root = str(Path(__file__).parent.parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from beanie import PydanticObjectId

from config.logging_config import get_logger
from config.settings import Settings
from core.llm.prompts import (
    AWARDS_PROMPT,
    CAREER_SUMMARY_PROMPT,
    COVER_LETTER_PROMPT,
    EDUCATION_PROMPT,
    FOLDER_NAME_PROMPT,
    HEADER_PROMPT,
    JOB_TITLES_PROMPT,
    PERSONAL_INFORMATION_PROMPT,
    PROJECTS_PROMPT,
    PUBLICATIONS_PROMPT,
    SKILLS_PROMPT,
    SYSTEM_PROMPT,
    WORK_EXPERIENCE_PROMPT,
)
from core.models.user import User

settings = Settings()
logger = get_logger(__name__)


class PromptLoader:
    """A class to load and format prompts with user preferences.

    This loader accesses file-based prompts from the core/llm/prompts directory
    and formats them with user preferences when needed.
    """

    # Default values for prompt variables
    DEFAULT_VARIABLES = {
        "cover_letter_details_paragraphs": "4",
        "cover_letter_details_target_grade_level": "12",
        "life_story": "No personal story available.",
    }

    def __init__(self, user_id: Optional[str | PydanticObjectId] = None):
        """Initialize the PromptLoader with a user_id.

        Args:
            user_id: Optional user ID (can be either user_id or _id)
        """
        self.user_id = user_id
        self._preferences = None

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
        logger.debug(f"PromptLoader initialized with {len(self._prompt_map)} prompts")

    @property
    async def preferences(self) -> Optional[Dict[str, Any]]:
        """Lazy load user preferences."""
        if self._preferences is None and self.user_id:
            try:
                user = await User.get(self.user_id)
                if user and user.preferences:
                    self._preferences = user.preferences.model_dump()
                    logger.debug(f"Loaded preferences for user {self.user_id}")
            except Exception as e:
                logger.error(f"Error loading preferences: {e}")
                self._preferences = None
        return self._preferences

    async def _get_preference_variables(self) -> Dict[str, Any]:
        """Get variables from user preferences.

        Returns:
            Dictionary of variables for template substitution
        """
        variables = self.DEFAULT_VARIABLES.copy()
        prefs = await self.preferences
        if prefs:
            for category, values in prefs.items():
                if isinstance(values, dict):
                    for key, value in values.items():
                        variables[f"{category}_{key}"] = value
                else:
                    variables[category] = values
        return variables

    async def _add_life_story(self, variables: Dict[str, Any]) -> None:
        """Add life story to variables if available.

        Args:
            variables: Dictionary to add life story to
        """
        if not self.user_id:
            return

        try:
            user = await User.get(self.user_id)
            if user and hasattr(user, "life_story"):
                variables["life_story"] = user.life_story
                logger.debug("Added life story to prompt variables")
        except Exception as e:
            logger.error(f"Error adding life story: {e}")

    async def _format_prompt(
        self, prompt_name: str, add_life_story: bool = False
    ) -> str:
        """Format a prompt with user preferences.

        Args:
            prompt_name: Name of the prompt to format
            add_life_story: Whether to add life story to variables

        Returns:
            Formatted prompt string

        Raises:
            KeyError: If prompt_name is not found in prompt_map
        """
        try:
            # Get prompt template
            prompt = self._prompt_map[prompt_name]

            # Return unformatted prompt if no formatting needed
            if not self.user_id and not add_life_story:
                return str(prompt)

            # Get variables for formatting
            variables = await self._get_preference_variables()

            # Add life story if needed
            if add_life_story:
                await self._add_life_story(variables)

            # Format prompt with variables
            try:
                return prompt.format(**variables)
            except KeyError as e:
                missing_var = str(e).strip("'")
                logger.warning(f"Missing variable in prompt: {missing_var}")
                variables[missing_var] = "Not specified"
                return prompt.format(**variables)

        except KeyError:
            logger.error(f"Prompt not found: {prompt_name}")
            raise
        except Exception as e:
            logger.error(f"Error formatting prompt: {e}")
            raise

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
        return await self._format_prompt("cover_letter", add_life_story=True)

    def refresh_preferences(self) -> None:
        """Force reload of user preferences."""
        self._preferences = None
        logger.debug("User preferences cache cleared")

    async def get_all_prompt_names(self) -> List[str]:
        """Get a list of all available prompt names.

        Returns:
            List[str]: List of all prompt names that can be loaded
        """
        return list(self._prompt_map.keys())


async def test_prompt_loader():
    """Test the PromptLoader functionality."""
    logger = get_logger("prompt_loader_test")
    logger.info("Starting prompt loader test")

    # Initialize loader and run tests
    loader = PromptLoader()

    try:
        # List all available prompts
        logger.info("Available prompts:")
        for prompt_name in await loader.get_all_prompt_names():
            logger.info(f"- {prompt_name}")

        # Test loading key prompts
        test_cases = [
            ("System", loader.get_system_prompt()),
            ("Work Experience", loader.get_section_prompt("work_experience")),
            ("Career Summary", loader.get_section_prompt("career_summary")),
            ("Cover Letter", loader.get_cover_letter_prompt()),
        ]

        # Run tests
        for name, coro in test_cases:
            try:
                prompt = await coro
                preview = prompt[:100] + "..." if len(prompt) > 100 else prompt
                logger.info(f"{name} prompt loaded successfully")
                print(f"\n{name} Prompt Preview:")
                print("-" * 20)
                print(preview)
            except Exception as e:
                logger.error(f"Failed to load {name.lower()} prompt: {e}")

        logger.info("Prompt loader test completed")
    except Exception as e:
        logger.error(f"Test failed: {e}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_prompt_loader())
