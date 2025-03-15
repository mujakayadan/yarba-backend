"""LLM service for AI model operations."""

import logging
from typing import Any, Dict, List, Optional, Tuple, Type

from ..exceptions.base import InternalServerException
from .config import settings
from .prompt import PromptService

logger = logging.getLogger(__name__)


class LLMStrategy:
    """Base strategy for LLM operations."""

    def __init__(self, system_prompt: str):
        """
        Initialize the strategy.

        Args:
            system_prompt: System prompt for the LLM
        """
        self.system_prompt = system_prompt
        self.model = ""
        self.temperature = 0.7
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate_content(self, prompt: str, data: str, job_description: str) -> str:
        """
        Generate content using the LLM.

        Args:
            prompt: Prompt for the LLM
            data: Data to include in the prompt
            job_description: Job description to include in the prompt

        Returns:
            str: Generated content

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement generate_content")

    def create_folder_name(self, naming_prompt: str, job_description: str) -> str:
        """
        Create a folder name for a job application.

        Args:
            naming_prompt: Prompt for folder name generation
            job_description: Job description

        Returns:
            str: Generated folder name

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement create_folder_name")


class OpenAIStrategy(LLMStrategy):
    """Strategy for OpenAI models."""

    def __init__(self, system_prompt: str):
        """
        Initialize the OpenAI strategy.

        Args:
            system_prompt: System prompt for the LLM
        """
        super().__init__(system_prompt)
        self.model = settings.llm.openai.model_name
        self.temperature = settings.llm.openai.temperature

    def generate_content(self, prompt: str, data: str, job_description: str) -> str:
        """
        Generate content using OpenAI.

        Args:
            prompt: Prompt for the LLM
            data: Data to include in the prompt
            job_description: Job description to include in the prompt

        Returns:
            str: Generated content

        Raises:
            InternalServerException: If API call fails
        """
        try:
            import openai

            messages = [
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": f"Prompt: {prompt}\n\nData: {data}\n\nJob Description: {job_description}",
                },
            ]

            response = openai.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
            )

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"OpenAI API error: {str(e)}")
            raise InternalServerException(f"OpenAI API error: {str(e)}")

    def create_folder_name(self, naming_prompt: str, job_description: str) -> str:
        """
        Create a folder name using OpenAI.

        Args:
            naming_prompt: Prompt for folder name generation
            job_description: Job description

        Returns:
            str: Generated folder name

        Raises:
            InternalServerException: If API call fails
        """
        try:
            import openai

            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "user",
                    "content": f"{naming_prompt}\n\nJob Description: {job_description}",
                },
            ]

            response = openai.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            self.logger.error(f"OpenAI API error: {str(e)}")
            raise InternalServerException(f"OpenAI API error: {str(e)}")


class ClaudeStrategy(LLMStrategy):
    """Strategy for Anthropic Claude models."""

    def __init__(self, system_prompt: str):
        """
        Initialize the Claude strategy.

        Args:
            system_prompt: System prompt for the LLM
        """
        super().__init__(system_prompt)
        self.model = settings.llm.claude.model_name
        self.temperature = settings.llm.claude.temperature

    def generate_content(self, prompt: str, data: str, job_description: str) -> str:
        """
        Generate content using Claude.

        Args:
            prompt: Prompt for the LLM
            data: Data to include in the prompt
            job_description: Job description to include in the prompt

        Returns:
            str: Generated content

        Raises:
            InternalServerException: If API call fails
        """
        try:
            import anthropic

            client = anthropic.Anthropic(
                api_key=settings.llm.claude.api_key.get_secret_value()
            )

            message = client.messages.create(
                model=self.model,
                system=self.system_prompt,
                max_tokens=4000,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": f"Prompt: {prompt}\n\nData: {data}\n\nJob Description: {job_description}",
                    }
                ],
            )

            return message.content[0].text

        except Exception as e:
            self.logger.error(f"Claude API error: {str(e)}")
            raise InternalServerException(f"Claude API error: {str(e)}")

    def create_folder_name(self, naming_prompt: str, job_description: str) -> str:
        """
        Create a folder name using Claude.

        Args:
            naming_prompt: Prompt for folder name generation
            job_description: Job description

        Returns:
            str: Generated folder name

        Raises:
            InternalServerException: If API call fails
        """
        try:
            import anthropic

            client = anthropic.Anthropic(
                api_key=settings.llm.claude.api_key.get_secret_value()
            )

            message = client.messages.create(
                model=self.model,
                system="You are a helpful assistant.",
                max_tokens=100,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": f"{naming_prompt}\n\nJob Description: {job_description}",
                    }
                ],
            )

            return message.content[0].text.strip()

        except Exception as e:
            self.logger.error(f"Claude API error: {str(e)}")
            raise InternalServerException(f"Claude API error: {str(e)}")


class LLMService:
    """Service for LLM operations."""

    def __init__(self, prompt_service: PromptService):
        """
        Initialize the LLM service.

        Args:
            prompt_service: Prompt service instance
        """
        self.prompt_service = prompt_service
        self.strategy = self._create_default_strategy()
        self.logger = logging.getLogger(self.__class__.__name__)

    def _create_default_strategy(self) -> LLMStrategy:
        """
        Create the default LLM strategy based on configuration.

        Returns:
            LLMStrategy: Default LLM strategy
        """
        provider = settings.llm.default_provider

        if provider == "openai":
            return OpenAIStrategy("You are a helpful assistant.")
        elif provider == "claude":
            return ClaudeStrategy("You are a helpful assistant.")
        else:
            self.logger.warning(
                f"Unsupported provider: {provider}, falling back to OpenAI"
            )
            return OpenAIStrategy("You are a helpful assistant.")

    async def configure(
        self,
        provider: str,
        model: str,
        temperature: float,
        user_id: Optional[str] = None,
    ) -> None:
        """
        Configure the LLM service.

        Args:
            provider: LLM provider (e.g., 'openai', 'claude')
            model: Model name
            temperature: Temperature for generation
            user_id: Optional user ID for personalized system prompt

        Raises:
            ValueError: If provider is not supported
        """
        system_prompt = await self.prompt_service.get_system_prompt(user_id)

        if provider == "openai":
            self.strategy = OpenAIStrategy(system_prompt)
        elif provider == "claude":
            self.strategy = ClaudeStrategy(system_prompt)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        self.strategy.model = model
        self.strategy.temperature = temperature

        self.logger.info(
            f"Configured LLM service with provider: {provider}, model: {model}"
        )

    async def generate_content(
        self, prompt: str, data: str, job_description: str
    ) -> str:
        """
        Generate content using the configured LLM.

        Args:
            prompt: Prompt for the LLM
            data: Data to include in the prompt
            job_description: Job description to include in the prompt

        Returns:
            str: Generated content

        Raises:
            InternalServerException: If generation fails
        """
        try:
            return self.strategy.generate_content(prompt, data, job_description)
        except Exception as e:
            self.logger.error(f"Error generating content: {str(e)}")
            raise InternalServerException(f"Error generating content: {str(e)}")

    async def create_company_name_and_job_title(
        self, job_description: str, user_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Create company name and job title from job description.

        Args:
            job_description: Job description
            user_id: Optional user ID for personalized prompt

        Returns:
            Tuple[str, str]: Company name and job title

        Raises:
            InternalServerException: If generation fails
        """
        try:
            naming_prompt = await self.prompt_service.get_folder_name_prompt(user_id)
            result = self.strategy.create_folder_name(naming_prompt, job_description)

            # Parse result to extract company name and job title
            parts = result.split(",", 1)
            if len(parts) == 2:
                company_name = parts[0].strip()
                job_title = parts[1].strip()
            else:
                company_name = result.strip()
                job_title = "Job Application"

            return company_name, job_title

        except Exception as e:
            self.logger.error(f"Error creating company name and job title: {str(e)}")
            raise InternalServerException(
                f"Error creating company name and job title: {str(e)}"
            )

    def get_config(self) -> Dict[str, Any]:
        """
        Get the current LLM configuration.

        Returns:
            Dict[str, Any]: Current configuration
        """
        return {
            "provider": self.strategy.__class__.__name__.replace("Strategy", ""),
            "model": self.strategy.model,
            "temperature": self.strategy.temperature,
        }

    async def set_config(
        self, config: Dict[str, Any], user_id: Optional[str] = None
    ) -> None:
        """
        Set the LLM configuration.

        Args:
            config: Configuration dictionary
            user_id: Optional user ID for personalized system prompt

        Raises:
            ValueError: If provider is not supported
        """
        await self.configure(
            provider=config["provider"].lower(),
            model=config["model"],
            temperature=config["temperature"],
            user_id=user_id,
        )
