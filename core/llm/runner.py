"""LLM runner implementation."""

from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel

from config import get_logger

from .base import BaseLLM, LLMConfig
from .openai_llm import OpenAILLM

logger = get_logger(__name__)


class RunnerConfig(BaseModel):
    """Configuration for LLM runner.

    This class holds configuration options for the LLM runner,
    including model selection and operation parameters.
    """

    llm_type: str = "openai"
    max_retries: int = 3
    timeout: int = 60
    cache_results: bool = True
    validate_responses: bool = True


class LLMRunner:
    """Runner class for managing LLM operations.

    This class provides a high-level interface for running LLM operations,
    managing different LLM implementations, and handling responses.
    """

    _llm_registry: Dict[str, Type[BaseLLM]] = {
        "openai": OpenAILLM,
    }

    def __init__(
        self,
        config: Optional[RunnerConfig] = None,
        llm_config: Optional[LLMConfig] = None,
    ):
        """Initialize the LLM runner.

        Args:
            config: Optional runner configuration
            llm_config: Optional LLM configuration
        """
        self.config = config or RunnerConfig()
        self.llm_config = llm_config
        self.llm = self._create_llm()
        self._response_cache: Dict[str, str] = {}

    def _create_llm(self) -> BaseLLM:
        """Create an LLM instance based on configuration.

        Returns:
            BaseLLM: Configured LLM instance
        """
        llm_class = self._llm_registry.get(self.config.llm_type)
        if not llm_class:
            raise ValueError(f"Unsupported LLM type: {self.config.llm_type}")
        return llm_class(self.llm_config)

    def register_llm(self, name: str, llm_class: Type[BaseLLM]) -> None:
        """Register a new LLM implementation.

        Args:
            name: Name for the LLM implementation
            llm_class: LLM class to register
        """
        self._llm_registry[name] = llm_class

    async def generate(
        self, prompt: str, cache_key: Optional[str] = None, **kwargs
    ) -> Optional[str]:
        """Generate text using the configured LLM.

        Args:
            prompt: Input prompt text
            cache_key: Optional key for caching results
            **kwargs: Additional model parameters

        Returns:
            Optional[str]: Generated text if successful, None otherwise
        """
        # Check cache if enabled
        if self.config.cache_results and cache_key:
            cached = self._response_cache.get(cache_key)
            if cached:
                return cached

        # Generate response
        response = await self.llm.generate(prompt, **kwargs)

        # Validate if enabled
        if response and self.config.validate_responses:
            if not await self.llm.validate_response(response, **kwargs):
                logger.warning("Response validation failed")
                return None

        # Cache if enabled
        if response and self.config.cache_results and cache_key:
            self._response_cache[cache_key] = response

        return response

    async def generate_with_context(
        self,
        prompt: str,
        context: List[Dict[str, Any]],
        cache_key: Optional[str] = None,
        **kwargs,
    ) -> Optional[str]:
        """Generate text using the configured LLM with context.

        Args:
            prompt: Input prompt text
            context: List of previous conversation turns
            cache_key: Optional key for caching results
            **kwargs: Additional model parameters

        Returns:
            Optional[str]: Generated text if successful, None otherwise
        """
        # Check cache if enabled
        if self.config.cache_results and cache_key:
            cached = self._response_cache.get(cache_key)
            if cached:
                return cached

        # Generate response
        response = await self.llm.generate_with_context(prompt, context, **kwargs)

        # Validate if enabled
        if response and self.config.validate_responses:
            if not await self.llm.validate_response(response, **kwargs):
                logger.warning("Response validation failed")
                return None

        # Cache if enabled
        if response and self.config.cache_results and cache_key:
            self._response_cache[cache_key] = response

        return response

    def clear_cache(self) -> None:
        """Clear the response cache."""
        self._response_cache.clear()
