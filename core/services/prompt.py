"""Prompt service for loading and managing prompts."""

import sys
import logging
from pathlib import Path
from string import Template
from typing import Any, Dict, List, Optional, Union

# Add project root to Python path when running as script
if __name__ == "__main__":
    project_root = str(Path(__file__).parent.parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from beanie import PydanticObjectId

from core.exceptions.base import NotFoundException
from core.models.user import User
from core.repositories.user import UserRepository
from core.loaders.prompt_loader import PromptLoader
from config.logging_config import get_logger
from config.settings import Settings

settings = Settings()
logger = get_logger(__name__)


class PromptService:
    """Service for loading and managing prompts for LLM operations.
    
    This service can load prompts from both:
    1. Text files (legacy approach)
    2. Python modules (new approach)
    """

    # Default values for prompt variables
    DEFAULT_VARIABLES = {
        "cover_letter_details_paragraphs": "4",
        "cover_letter_details_target_grade_level": "12",
        "life_story": "No personal story available.",
    }

    def __init__(
        self, 
        user_repository: Optional[UserRepository] = None, 
        user_id: Optional[Union[str, PydanticObjectId]] = None,
        use_python_prompts: bool = True
    ):
        """
        Initialize the prompt service.

        Args:
            user_repository: User repository instance (required for file-based prompts)
            user_id: User ID for personalized prompts (required for Python-based prompts)
            use_python_prompts: Whether to use Python module-based prompts (True) or file-based prompts (False)
        """
        self.prompt_dir = Path(settings.paths.prompts_dir)
        self.user_repository = user_repository
        self.user_id = user_id
        self.use_python_prompts = use_python_prompts
        self.logger = get_logger(self.__class__.__name__)
        
        # Initialize the Python module-based prompt loader if needed
        if use_python_prompts:
            self.prompt_loader = PromptLoader(user_id)
            logger.debug(f"Using Python module-based prompts")
        else:
            logger.debug(f"Using file-based prompts")

    async def _get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user preferences using the repository.

        Args:
            user_id: User ID

        Returns:
            Optional[Dict[str, Any]]: User preferences if found, None otherwise
        """
        if not self.user_repository:
            self.logger.warning("User repository not provided, cannot fetch preferences")
            return None
            
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
        variables = self.DEFAULT_VARIABLES.copy()
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
        if not self.user_repository:
            variables["life_story"] = "No personal story available."
            return
            
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
        if self.use_python_prompts:
            return await self.prompt_loader.get_section_prompt(section)
        else:
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
        if self.use_python_prompts:
            return await self.prompt_loader.get_system_prompt()
        else:
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
        if self.use_python_prompts:
            return await self.prompt_loader.get_folder_name_prompt()
        else:
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
        if self.use_python_prompts:
            return await self.prompt_loader.get_cover_letter_prompt()
        else:
            return await self.load_prompt("cover_letter_prompt.txt", user_id)
    
    async def get_available_prompts(self) -> List[str]:
        """
        Get a list of all available prompts.
        
        Returns:
            List of prompt names that can be accessed
        """
        if self.use_python_prompts:
            return await self.prompt_loader.get_all_prompt_names()
        else:
            # List all txt files in the prompts directory
            prompt_files = [f.stem.replace('_prompt', '') for f in self.prompt_dir.glob("*_prompt.txt")]
            return prompt_files
    
    async def get_multiple_prompts(self, names: List[str]) -> Dict[str, str]:
        """
        Get multiple prompts by name.
        
        Args:
            names: List of prompt names to retrieve
            
        Returns:
            Dictionary mapping prompt names to their formatted text
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
        if self.use_python_prompts:
            self.prompt_loader = PromptLoader(user_id)
        self.logger.debug(f"User changed to: {user_id}")
    
    def switch_prompt_source(self, use_python_prompts: bool) -> None:
        """
        Switch between Python module-based prompts and file-based prompts.
        
        Args:
            use_python_prompts: True to use Python modules, False to use files
        """
        if use_python_prompts != self.use_python_prompts:
            self.use_python_prompts = use_python_prompts
            if use_python_prompts:
                self.prompt_loader = PromptLoader(self.user_id)
                self.logger.debug("Switched to Python module-based prompts")
            else:
                self.logger.debug("Switched to file-based prompts")


# Simple usage example
async def test_prompt_service():
    """Test both prompt service approaches."""
    logger = get_logger("prompt_service_test")
    logger.info("Starting prompt service test")
    
    # Test Python module-based prompts
    logger.info("Testing Python module-based prompts:")
    python_service = PromptService(use_python_prompts=True)
    
    # Get available prompts
    py_prompts = await python_service.get_available_prompts()
    logger.info(f"Available Python prompts: {', '.join(py_prompts)}")
    
    # Test key prompts
    try:
        system_prompt = await python_service.get_system_prompt()
        career_prompt = await python_service.get_section_prompt("career_summary")
        
        print("\nPYTHON MODULE PROMPTS:")
        print("=" * 40)
        print(f"System prompt preview: {system_prompt[:100]}...")
        print(f"Career summary prompt preview: {career_prompt[:100]}...")
    except Exception as e:
        logger.error(f"Error testing Python prompts: {e}")
    
    # Try to test file-based prompts if the directory exists
    prompt_dir = Path(settings.paths.prompts_dir)
    if prompt_dir.exists():
        logger.info("\nTesting file-based prompts:")
        file_service = PromptService(use_python_prompts=False)
        
        try:
            # Get available prompts
            file_prompts = await file_service.get_available_prompts()
            logger.info(f"Available file prompts: {', '.join(file_prompts)}")
            
            if file_prompts:
                sample_prompt = await file_service.get_section_prompt(file_prompts[0])
                print("\nFILE-BASED PROMPTS:")
                print("=" * 40)
                print(f"{file_prompts[0]} prompt preview: {sample_prompt[:100]}...")
        except Exception as e:
            logger.error(f"Error testing file-based prompts: {e}")
    else:
        logger.warning(f"Prompt directory {prompt_dir} not found, skipping file-based tests")
    
    logger.info("PromptService test completed")


if __name__ == "__main__":
    import asyncio
    
    asyncio.run(test_prompt_service())
