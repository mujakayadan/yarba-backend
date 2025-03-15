"""Prompt loader for loading and formatting prompts."""

import asyncio
import logging
import os
from pathlib import Path
from string import Template
from typing import Any, Dict, Optional

from beanie import PydanticObjectId

from config.settings import Settings
from core.models.user import User

logger = logging.getLogger(__name__)
settings = Settings()


class PromptLoader:
    """A class to load prompts from a specified directory."""

    def __init__(self, user_id: Optional[str | PydanticObjectId] = None):
        """Initialize the PromptLoader with a base directory path and user_id.

        Args:
            user_id: Optional user ID (can be either user_id or _id)
        """
        # Get the absolute path to the prompts directory
        current_dir = Path(__file__).parent.parent
        self.prompt_dir = current_dir / "llm" / "prompts"
        self.user_id = user_id
        self._preferences = None

    @property
    async def preferences(self) -> Optional[Dict[str, Any]]:
        """Lazy load user preferences."""
        if self._preferences is None and self.user_id:
            try:
                user = await User.get(self.user_id)
                if user and user.preferences:
                    self._preferences = user.preferences.model_dump()
                    logger.debug(f"Loaded preferences: {self._preferences}")
            except Exception as e:
                logger.error(f"Error loading preferences for user {self.user_id}: {e}")
                self._preferences = None
        return self._preferences

    def _read_template_file(self, filename: str) -> Template:
        """Read and create a template from a file.

        Args:
            filename: Name of the file to read

        Returns:
            Template object created from file contents

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        prompt_path = self.prompt_dir / filename
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found at {prompt_path}")

        with open(prompt_path, "r", encoding="utf-8") as f:
            return Template(f.read().strip())

    async def _get_preference_variables(self) -> Dict[str, Any]:
        """Get variables from user preferences.

        Returns:
            Dictionary of variables for template substitution
        """
        variables = {}
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
        try:
            user = await User.get(self.user_id)
            if user and hasattr(user, "life_story"):
                variables["life_story"] = user.life_story
            else:
                variables["life_story"] = "No personal story available."
        except Exception as e:
            logger.error(f"Error loading life story: {e}")
            variables["life_story"] = "No personal story available."

    async def _load_prompt(self, filename: str) -> str:
        """Load and format a prompt file with user preferences if available.

        Args:
            filename: The name of the file to load

        Returns:
            Formatted prompt string
        """
        try:
            template = self._read_template_file(filename)
            variables = await self._get_preference_variables()

            # Add life story if loading cover letter prompt
            if filename == "cover_letter_prompt.txt" and self.user_id:
                await self._add_life_story(variables)

            return template.safe_substitute(variables)
        except Exception as e:
            logger.error(f"Error loading prompt {filename}: {e}")
            raise

    async def get_section_prompt(self, section: str) -> str:
        """Get the prompt for a specific section with user preferences.

        Args:
            section: The section name (e.g. 'career_summary', 'skills')

        Returns:
            str: The formatted prompt text

        Raises:
            FileNotFoundError: If prompt file doesn't exist
            TemplateError: If template substitution fails
        """
        filename = f"{section.lower()}_prompt.txt"
        return await self._load_prompt(filename)

    async def get_system_prompt(self) -> str:
        """Get the system prompt."""
        return await self._load_prompt("system_prompt.txt")

    async def get_folder_name_prompt(self) -> str:
        """Get the folder name prompt."""
        return await self._load_prompt("folder_name_prompt.txt")

    async def get_cover_letter_prompt(self) -> str:
        """Get the cover letter prompt with user's life story.

        Returns:
            str: The cover letter prompt with user's life story
        """
        return await self._load_prompt("cover_letter_prompt.txt")

    def refresh_preferences(self) -> None:
        """Force reload of user preferences."""
        self._preferences = None


async def main():
    """Main function to test the PromptLoader."""
    # Initialize MongoDB connection
    await init_beanie(
        database=AsyncIOMotorClient(settings.database.url)[settings.database.name],
        document_models=[User],
    )

    # Create a test user if needed
    test_user = await User.find_one(User.email == "test@example.com")
    if not test_user:
        test_user = User(
            email="test@example.com",
            hashed_password="test",
            full_name="Test User",
        )
        await test_user.insert()

    # Example usage
    prompt_loader = PromptLoader(user_id=test_user.id)
    print(f"Resolved PROMPTS_FOLDER: {prompt_loader.prompt_dir}\n")

    try:
        # Try loading each available prompt
        prompts = [
            "personal_information",
            "skills",
            "work_experience",
            "projects",
            "publications",
            "education",
            "career_summary",
            "cover_letter",
            "awards",
        ]

        for section in prompts:
            try:
                prompt = await prompt_loader.get_section_prompt(section)
                print(f"\n{'='*40}")
                print(f"{section.upper()} PROMPT")
                print(f"{'='*40}\n")
                # Split into lines and print first 5 lines
                lines = prompt.split("\n")
                preview = "\n".join(lines[:5])
                print(preview)
                if len(lines) > 5:
                    print("\n... (truncated)")
            except FileNotFoundError as e:
                print(f"\nError loading {section} prompt: {e}")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    # Import here to avoid circular imports
    from motor.motor_asyncio import AsyncIOMotorClient
    from beanie import init_beanie

    # Run the async main function
    asyncio.run(main())
