"""Base LLM implementation."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from config import get_logger

logger = get_logger(__name__)


class LLMConfig(BaseModel):
    """Configuration for LLM models.

    This class holds configuration options for LLM models,
    including API keys, model parameters, and other settings.
    """

    model_name: str
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: Optional[List[str]] = None
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 1


class BaseLLM(ABC):
    """Abstract base class for LLM implementations.

    This class provides the base functionality for interacting with
    different LLM models. It handles configuration, prompting,
    and response processing.
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize the LLM.

        Args:
            config: Optional LLM configuration
        """
        self.config = config or LLMConfig(model_name="default")

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> Optional[str]:
        """Generate text from a prompt.

        Args:
            prompt: Input prompt text
            **kwargs: Additional model-specific parameters

        Returns:
            Optional[str]: Generated text if successful, None otherwise
        """
        pass

    @abstractmethod
    async def generate_with_context(
        self, prompt: str, context: List[Dict[str, Any]], **kwargs
    ) -> Optional[str]:
        """Generate text from a prompt with conversation context.

        Args:
            prompt: Input prompt text
            context: List of previous conversation turns
            **kwargs: Additional model-specific parameters

        Returns:
            Optional[str]: Generated text if successful, None otherwise
        """
        pass

    @abstractmethod
    async def validate_response(self, response: str, **kwargs) -> bool:
        """Validate a model's response.

        Args:
            response: Response text to validate
            **kwargs: Additional validation parameters

        Returns:
            bool: True if validation passes, False otherwise
        """
        pass

    async def _handle_error(self, error: Exception) -> None:
        """Handle errors during LLM operations.

        Args:
            error: The exception that occurred
        """
        logger.error(f"Error in LLM operation: {str(error)}")
        # Additional error handling logic can be added here
