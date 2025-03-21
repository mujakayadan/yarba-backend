"""Service for LLM operations using LiteLLM as an abstraction layer."""

import asyncio
from typing import Any, Dict, List, Optional, Union

import litellm
from litellm import acompletion

from config.logging_config import get_logger
from config.settings import Settings
from core.models.profile import Profile
from core.repositories.profile_repository import ProfileRepository
from core.services.prompt_service import PromptService

settings = Settings()
logger = get_logger(__name__)


class LLMService:
    """
    Service for handling LLM operations using LiteLLM as an abstraction layer.

    This service provides a unified interface to multiple LLM providers
    and handles prompt formatting, API key management, and response processing.
    """

    def __init__(
        self,
        profile_repository: Optional[ProfileRepository] = None,
        prompt_service: Optional[PromptService] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """
        Initialize the LLM service.

        Args:
            profile_repository: Repository for accessing user profiles and preferences
            prompt_service: Service for loading and formatting prompts
            model: Override the default model from settings
            api_key: Override the default API key from settings
            temperature: Override the default temperature from settings
        """
        self.profile_repository = profile_repository
        self.prompt_service = prompt_service

        # Set default values from settings
        self.model = model or settings.llm.default_model
        self.api_key = api_key
        self.temperature = temperature or settings.llm.temperature
        self.max_tokens = settings.llm.max_tokens

        self.logger = get_logger(self.__class__.__name__)
        self.logger.info(f"LLM service initialized with model: {self.model}")

        # Configure LiteLLM
        self._configure_litellm()

    def _configure_litellm(self) -> None:
        """Configure litellm with default settings."""
        # Set fallback providers if needed
        litellm.set_verbose = False

        # Set API keys from settings if available
        if settings.llm.openai_api_key:
            litellm.api_key_dict["openai"] = settings.llm.openai_api_key
        if settings.llm.anthropic_api_key:
            litellm.api_key_dict["anthropic"] = settings.llm.anthropic_api_key
        if settings.llm.gemini_api_key:
            litellm.api_key_dict["gemini"] = settings.llm.gemini_api_key

        # Override with provided API key if specified
        if self.api_key:
            # Detect the provider from the model name
            provider = self._get_provider_from_model(self.model)
            if provider:
                litellm.api_key_dict[provider] = self.api_key

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
            return "gemini"
        elif "command" in model_lower:
            return "cohere"
        elif "llama" in model_lower or "mistral" in model_lower:
            return "mistral"
        else:
            return None

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

    async def _get_api_key_for_user(self, user_id: str, model: str) -> Optional[str]:
        """
        Get the appropriate API key for a user and model.

        Args:
            user_id: User ID
            model: Model name

        Returns:
            API key if available
        """
        if not self.profile_repository:
            return None

        try:
            profile = await self.profile_repository.get_by_user_id(user_id)
            if not profile or not profile.api_keys:
                return None

            provider = self._get_provider_from_model(model)
            if not provider:
                return None

            key_name = f"{provider.upper()}_API_KEY"
            return profile.api_keys.get(key_name)
        except Exception as e:
            self.logger.error(f"Error fetching API key: {e}")

        return None

    async def configure_for_user(self, user_id: str) -> None:
        """
        Configure the LLM service for a specific user.

        Args:
            user_id: User ID to configure for
        """
        # Get user preferences
        preferences = await self._get_user_preferences(user_id)

        # Apply user-specific settings if available
        self.model = preferences.get("model_name", self.model)
        self.temperature = preferences.get("temperature", self.temperature)
        self.max_tokens = preferences.get("max_tokens", self.max_tokens)

        # Try to get user-specific API key
        api_key = await self._get_api_key_for_user(user_id, self.model)
        if api_key:
            provider = self._get_provider_from_model(self.model)
            if provider:
                litellm.api_key_dict[provider] = api_key

        # Configure prompt service if available
        if self.prompt_service:
            self.prompt_service.set_user_id(user_id)

        self.logger.debug(f"LLM service configured for user {user_id}")

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

            # Log the request
            self.logger.debug(
                f"Sending request to {model} with temperature {temperature}"
            )

            # Call the LLM
            response = await acompletion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Process the response
            content = response.choices[0].message.content
            return content

        except Exception as e:
            self.logger.error(f"Error getting completion: {e}")
            raise

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
