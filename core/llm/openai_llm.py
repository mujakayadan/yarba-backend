"""OpenAI LLM implementation."""

import asyncio
from typing import Any, Dict, List, Optional

import openai
from openai import AsyncOpenAI

from config import get_logger

from .base import BaseLLM, LLMConfig

logger = get_logger(__name__)


class OpenAIConfig(LLMConfig):
    """Configuration for OpenAI models.

    This class extends the base LLM configuration with
    OpenAI-specific settings.
    """

    organization_id: Optional[str] = None
    model_name: str = "gpt-4-turbo-preview"
    system_prompt: Optional[str] = None


class OpenAILLM(BaseLLM):
    """OpenAI LLM implementation.

    This class provides integration with OpenAI's language models,
    supporting both chat and completion endpoints.
    """

    def __init__(self, config: Optional[OpenAIConfig] = None):
        """Initialize the OpenAI LLM.

        Args:
            config: Optional OpenAI configuration
        """
        super().__init__(config or OpenAIConfig())
        self.client = AsyncOpenAI(
            api_key=self.config.api_key,
            organization=self.config.organization_id,
            timeout=self.config.timeout,
        )

    async def generate(self, prompt: str, **kwargs) -> Optional[str]:
        """Generate text using OpenAI's API.

        Args:
            prompt: Input prompt text
            **kwargs: Additional model parameters

        Returns:
            Optional[str]: Generated text if successful, None otherwise
        """
        try:
            messages = []
            if self.config.system_prompt:
                messages.append(
                    {"role": "system", "content": self.config.system_prompt}
                )
            messages.append({"role": "user", "content": prompt})

            for attempt in range(self.config.retry_attempts):
                try:
                    response = await self.client.chat.completions.create(
                        model=self.config.model_name,
                        messages=messages,
                        temperature=self.config.temperature,
                        max_tokens=self.config.max_tokens,
                        top_p=self.config.top_p,
                        frequency_penalty=self.config.frequency_penalty,
                        presence_penalty=self.config.presence_penalty,
                        stop=self.config.stop_sequences,
                        **kwargs,
                    )
                    return response.choices[0].message.content
                except openai.RateLimitError:
                    if attempt < self.config.retry_attempts - 1:
                        await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                    else:
                        raise

        except Exception as e:
            await self._handle_error(e)
            return None

    async def generate_with_context(
        self, prompt: str, context: List[Dict[str, Any]], **kwargs
    ) -> Optional[str]:
        """Generate text using OpenAI's API with conversation context.

        Args:
            prompt: Input prompt text
            context: List of previous conversation turns
            **kwargs: Additional model parameters

        Returns:
            Optional[str]: Generated text if successful, None otherwise
        """
        try:
            messages = []
            if self.config.system_prompt:
                messages.append(
                    {"role": "system", "content": self.config.system_prompt}
                )

            # Add conversation context
            for turn in context:
                messages.append(
                    {"role": turn.get("role", "user"), "content": turn["content"]}
                )

            # Add current prompt
            messages.append({"role": "user", "content": prompt})

            for attempt in range(self.config.retry_attempts):
                try:
                    response = await self.client.chat.completions.create(
                        model=self.config.model_name,
                        messages=messages,
                        temperature=self.config.temperature,
                        max_tokens=self.config.max_tokens,
                        top_p=self.config.top_p,
                        frequency_penalty=self.config.frequency_penalty,
                        presence_penalty=self.config.presence_penalty,
                        stop=self.config.stop_sequences,
                        **kwargs,
                    )
                    return response.choices[0].message.content
                except openai.RateLimitError:
                    if attempt < self.config.retry_attempts - 1:
                        await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                    else:
                        raise

        except Exception as e:
            await self._handle_error(e)
            return None

    async def validate_response(self, response: str, **kwargs) -> bool:
        """Validate OpenAI's response.

        Args:
            response: Response text to validate
            **kwargs: Additional validation parameters

        Returns:
            bool: True if validation passes, False otherwise
        """
        # Basic validation
        if not response or not isinstance(response, str):
            return False

        # Length validation
        min_length = kwargs.get("min_length", 1)
        max_length = kwargs.get("max_length", float("inf"))
        if not min_length <= len(response) <= max_length:
            return False

        # Content validation can be added here
        return True
