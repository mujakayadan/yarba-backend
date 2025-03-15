"""Token counting utilities for LLM interactions."""

from typing import Dict, List, Optional, Union

import tiktoken
from anthropic import Anthropic
from openai import OpenAI

from config.logging_config import get_logger
from config.settings import Settings

logger = get_logger(__name__)
settings = Settings()


def count_tokens_openai(
    text: str,
    model: Optional[str] = None,
) -> int:
    """
    Count tokens for OpenAI models.

    Args:
        text: Text to count tokens for
        model: Model name (defaults to settings)

    Returns:
        int: Number of tokens
    """
    if not text:
        return 0

    model = model or settings.llm.openai.model_name

    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        logger.error(f"Error counting tokens for OpenAI: {e}")
        # Fallback to approximate count
        return len(text.split()) * 1.3


def count_tokens_anthropic(
    text: str,
    model: Optional[str] = None,
) -> int:
    """
    Count tokens for Anthropic models.

    Args:
        text: Text to count tokens for
        model: Model name (defaults to settings)

    Returns:
        int: Number of tokens
    """
    if not text:
        return 0

    model = model or settings.llm.anthropic.model_name

    try:
        client = Anthropic()
        return client.count_tokens(text)
    except Exception as e:
        logger.error(f"Error counting tokens for Anthropic: {e}")
        # Fallback to approximate count
        return len(text.split()) * 1.3


def count_tokens(
    text: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> int:
    """
    Count tokens for the specified provider and model.

    Args:
        text: Text to count tokens for
        provider: Provider name (defaults to settings)
        model: Model name (defaults to settings)

    Returns:
        int: Number of tokens
    """
    if not text:
        return 0

    provider = provider or settings.llm.provider

    if provider.lower() == "openai":
        return count_tokens_openai(text, model)
    elif provider.lower() == "anthropic":
        return count_tokens_anthropic(text, model)
    else:
        logger.warning(f"Unsupported provider: {provider}, using approximate count")
        return len(text.split()) * 1.3  # Approximate token count
