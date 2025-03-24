"""Service for LLM operations using LiteLLM as an abstraction layer."""

import asyncio
from typing import Any, Dict, List, Optional, Tuple, Union

import litellm
from beanie.odm.fields import PydanticObjectId
from litellm import acompletion

from config.logging_config import get_logger
from config.settings import settings
from core.models.profile import Profile
from core.repositories.profile_repository import ProfileRepository
from core.services.prompt_service import PromptService

logger = get_logger(__name__)


class LLMService:
    """
    Service for handling LLM operations using LiteLLM as an abstraction layer.

    This service provides a unified interface to multiple LLM providers
    and handles prompt formatting, API key management, and response processing.
    """

    def __init__(
        self,
        profile_repository: ProfileRepository,
        prompt_service: Optional[PromptService] = None,
        model: str = "claude-3-5-sonnet-20240620",
        temperature: float = 0.1,
    ):
        """
        Initialize the LLM service.

        Args:
            profile_repository: Repository for accessing user profiles and preferences
            prompt_service: Service for loading and formatting prompts
            model: Override the default model from settings
            temperature: Override the default temperature from settings
        """
        self.profile_repository = profile_repository
        self.prompt_service = prompt_service
        self.model = model
        self.temperature = temperature
        self.max_tokens = settings.llm.max_tokens

        # Store API keys from environment config as fallbacks
        self.api_keys = {
            "openai": settings.llm.openai_api_key,
            "anthropic": settings.llm.anthropic_api_key,
            "google": settings.llm.gemini_api_key,
            "cohere": None,
            "mistral": None,
        }

        self._setup_litellm()
        self.logger = get_logger(self.__class__.__name__)
        self.logger.info(f"LLM service initialized with model: {self.model}")

    def _setup_litellm(self):
        """Set up litellm with API keys."""
        # Configure litellm with API keys
        try:
            litellm.api_key_dict = {
                "openai": self.api_keys["openai"],
                "anthropic": self.api_keys["anthropic"],
                "google": self.api_keys["google"],
            }
            logger.debug("LiteLLM configured with API keys")
        except Exception as e:
            logger.error(f"Error configuring LiteLLM: {e}")
            raise

    async def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Get LLM preferences for a user.

        Args:
            user_id: User ID

        Returns:
            Dictionary of LLM preferences
        """
        if not self.profile_repository:
            return {}

        try:
            profile = await self.profile_repository.get_by_user_id(user_id)
            if profile and profile.preferences and profile.preferences.llm_preferences:
                return profile.preferences.llm_preferences
        except Exception as e:
            self.logger.error(f"Error fetching user preferences: {e}")

        return {}

    async def _get_api_keys_for_user(self, user_id: str) -> Dict[str, str]:
        """
        Get all API keys for a user.

        Args:
            user_id: User ID

        Returns:
            Dictionary of API keys
        """
        if not self.profile_repository:
            return {}

        try:
            return await self.profile_repository.get_api_keys(user_id)
        except Exception as e:
            self.logger.error(f"Error fetching API keys: {e}")
            return {}

    async def configure_for_user(self, user_id: Union[str, PydanticObjectId]) -> None:
        """
        Configure the LLM service for a specific user.

        Args:
            user_id: User ID to configure for
        """
        try:
            # Get user profile
            profile = await self.profile_repository.get_by_user_id(user_id)

            if (
                profile
                and profile.preferences
                and "llm_preferences" in profile.preferences
            ):
                llm_prefs = profile.preferences["llm_preferences"]

                # Update model and temperature if specified
                if "model_name" in llm_prefs:
                    self.model = llm_prefs["model_name"]
                    logger.debug(f"Using model from user preferences: {self.model}")

                if "temperature" in llm_prefs:
                    self.temperature = llm_prefs["temperature"]
                    logger.debug(
                        f"Using temperature from user preferences: {self.temperature}"
                    )
            else:
                logger.debug("No user preferences found, using defaults")

            # Get all user API keys
            user_api_keys = await self._get_api_keys_for_user(user_id)

            # Update the service's API keys with user-specific keys if available
            if "OPENAI_API_KEY" in user_api_keys:
                self.api_keys["openai"] = user_api_keys["OPENAI_API_KEY"]
            if "ANTHROPIC_API_KEY" in user_api_keys:
                self.api_keys["anthropic"] = user_api_keys["ANTHROPIC_API_KEY"]
            if "GEMINI_API_KEY" in user_api_keys:
                self.api_keys["google"] = user_api_keys["GEMINI_API_KEY"]
            if "MISTRAL_API_KEY" in user_api_keys:
                self.api_keys["mistral"] = user_api_keys["MISTRAL_API_KEY"]
            if "COHERE_API_KEY" in user_api_keys:
                self.api_keys["cohere"] = user_api_keys["COHERE_API_KEY"]

            # Configure prompt service if available
            if self.prompt_service:
                self.prompt_service.set_user_id(user_id)

            self.logger.debug(f"LLM service configured for user {user_id}")
        except Exception as e:
            self.logger.error(f"Error configuring LLM for user {user_id}: {e}")

    async def get_prompt(self, prompt_name: str) -> str:
        """
        Get a prompt by name.

        Args:
            prompt_name: Name of the prompt

        Returns:
            Formatted prompt text

        Raises:
            ValueError: If prompt_service is not available
        """
        if not self.prompt_service:
            raise ValueError("Prompt service not available")

        return await self.prompt_service.get_prompt(prompt_name)

    async def get_section_prompt(self, section_name: str) -> str:
        """
        Get a prompt for a specific portfolio section.

        Args:
            section_name: Name of the section

        Returns:
            Formatted prompt text

        Raises:
            ValueError: If prompt_service is not available
        """
        if not self.prompt_service:
            raise ValueError("Prompt service not available")

        try:
            return await self.prompt_service.get_portfolio_section_prompt(section_name)
        except KeyError:
            # Fall back to regular section prompt
            return await self.prompt_service.get_section_prompt(section_name)

    async def get_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Get a completion from the LLM.

        Args:
            prompt: The prompt text
            system_prompt: Optional system prompt
            model: Optional model override
            temperature: Optional temperature override
            max_tokens: Optional max tokens override

        Returns:
            Completion text from the LLM
        """
        try:
            # Use provided values or fall back to instance defaults
            model = model or self.model
            temperature = temperature or self.temperature
            max_tokens = max_tokens or self.max_tokens

            # Prepare messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Get the provider for this model
            provider = self._get_provider_from_model(model)
            api_key = self.api_keys.get(provider) if provider else None

            # Log the request
            self.logger.debug(
                f"Sending request to {model} with temperature {temperature}"
            )

            # Call the LLM with the appropriate API key
            response = await acompletion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=api_key,  # Pass API key directly to the completion function
            )

            # Process the response
            content = response.choices[0].message.content
            return content

        except Exception as e:
            self.logger.error(f"Error getting completion: {e}")
            raise

    def _get_provider_from_model(self, model: str) -> Optional[str]:
        """
        Get the provider name from the model name.

        Args:
            model: Model name (e.g., 'gpt-4', 'claude-3-opus')

        Returns:
            Provider name or None if unknown
        """
        model_lower = model.lower()
        if "gpt" in model_lower or "text-embedding" in model_lower:
            return "openai"
        elif "claude" in model_lower:
            return "anthropic"
        elif "gemini" in model_lower:
            return "google"
        elif "command" in model_lower:
            return "cohere"
        elif "llama" in model_lower or "mistral" in model_lower:
            return "mistral"
        else:
            return None

    async def generate_section(
        self,
        section_name: str,
        context: Dict[str, Any],
        job_description: str,
    ) -> str:
        """
        Generate content for a resume section.

        Args:
            section_name: Name of the section to generate
            context: Context data for the generation
            job_description: Job description to target

        Returns:
            Generated section content
        """
        try:
            # Get the appropriate prompt for this section
            prompt_text = await self.get_section_prompt(section_name)

            # Get system prompt
            system_prompt = await self.prompt_service.get_system_prompt()

            # Combine prompt with context and job description
            full_prompt = f"""
Job Description:
{job_description}

{prompt_text}

Section Data:
{context}
"""

            # Get completion
            return await self.get_completion(
                prompt=full_prompt,
                system_prompt=system_prompt,
            )

        except Exception as e:
            self.logger.error(f"Error generating {section_name} section: {e}")
            raise

    async def generate_cover_letter(
        self,
        resume_content: Dict[str, Any],
        job_description: str,
        company_name: str,
        job_title: str,
    ) -> str:
        """
        Generate a cover letter based on resume content and job description.

        Args:
            resume_content: Resume content dictionary
            job_description: Job description text
            company_name: Company name
            job_title: Job title

        Returns:
            Generated cover letter text
        """
        try:
            # Get cover letter prompt
            prompt_text = await self.prompt_service.get_cover_letter_prompt()

            # Get system prompt
            system_prompt = await self.prompt_service.get_system_prompt()

            # Combine prompt with resume content and job details
            full_prompt = f"""
Job Title: {job_title}
Company Name: {company_name}
Job Description:
{job_description}

Resume Content:
{resume_content}

{prompt_text}
"""

            # Get completion
            return await self.get_completion(
                prompt=full_prompt,
                system_prompt=system_prompt,
                # Cover letters can be longer
                max_tokens=self.max_tokens * 2,
            )

        except Exception as e:
            self.logger.error(f"Error generating cover letter: {e}")
            raise

    async def extract_job_title_and_company(
        self, job_description: str
    ) -> Tuple[str, str]:
        """
        Extract job title and company name from a job description using LLM.

        Args:
            job_description: The job description text

        Returns:
            Tuple of (company_name, job_title)
        """
        try:
            # Get the folder name prompt
            folder_name_prompt = await self.prompt_service.get_folder_name_prompt()

            # Use the LLM service to get the completion
            system_prompt = await self.prompt_service.get_system_prompt()

            response = await self.get_completion(
                prompt=f"{folder_name_prompt}\n\nJob Description:\n{job_description}",
                system_prompt=system_prompt,
            )

            # Parse the response (expected format: company_name|job_title)
            if "|" in response:
                parts = response.strip().split("|")
                if len(parts) == 2:
                    company_name, job_title = parts
                    # Clean the values
                    company_name = company_name.strip().lower().replace(" ", "_")
                    job_title = job_title.strip().lower().replace(" ", "_")
                    return company_name, job_title

            # If parsing fails, return default values
            self.logger.warning(
                f"Failed to parse company/title from response: {response}"
            )
            return "unknown_company", "unknown_position"

        except Exception as e:
            self.logger.error(f"Error extracting job title and company: {e}")
            return "unknown_company", "unknown_position"
