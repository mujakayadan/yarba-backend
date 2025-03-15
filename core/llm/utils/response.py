"""Response processing utilities for LLM interactions."""

from typing import Any, Dict, Optional, Union

from core.llms.utils.errors import ResponseError

from config.logging_config import get_logger
from config.settings import Settings

logger = get_logger(__name__)
settings = Settings()


def process_api_response(
    response: Any,
    provider: Optional[str] = None,
    default_value: str = "",
) -> str:
    """
    Process API responses consistently across different providers.

    Args:
        response: Raw API response
        provider: LLM provider name
        default_value: Default value to return if processing fails

    Returns:
        str: Processed response text

    Raises:
        ResponseError: If response processing fails
    """
    if not response:
        return default_value

    try:
        # Get provider from settings if not provided
        provider = provider or settings.llm.provider

        # OpenAI response format
        if hasattr(response, "choices"):
            if not response.choices:
                return default_value
            return response.choices[0].message.content

        # Anthropic response format
        if hasattr(response, "content"):
            if not response.content:
                return default_value
            return response.content[0].text

        # Ollama response format
        if isinstance(response, dict):
            return response.get("response", default_value)

        # Gemini response format
        if provider.lower() == "gemini":
            return getattr(response, "text", default_value)

        # Unknown response format
        logger.warning(f"Unknown response format from {provider}")
        return str(response)

    except Exception as e:
        error_msg = f"Failed to process {provider} response: {e}"
        logger.error(error_msg)
        raise ResponseError(error_msg, provider=provider, response_data=response)


def extract_json_from_response(
    response: str,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extract JSON data from a response string.

    Args:
        response: Response string potentially containing JSON
        provider: LLM provider name

    Returns:
        Dict[str, Any]: Extracted JSON data

    Raises:
        ResponseError: If JSON extraction fails
    """
    import json
    import re

    try:
        # Get provider from settings if not provided
        provider = provider or settings.llm.provider

        # Try to find JSON-like content using regex
        json_pattern = r"\{(?:[^{}]|(?R))*\}"
        matches = re.findall(json_pattern, response)

        if not matches:
            raise ResponseError(
                "No JSON content found in response",
                provider=provider,
                response_data={"response": response},
            )

        # Try to parse each match as JSON
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        raise ResponseError(
            "Failed to parse JSON from response",
            provider=provider,
            response_data={"response": response},
        )

    except Exception as e:
        if not isinstance(e, ResponseError):
            error_msg = f"Error extracting JSON from response: {e}"
            logger.error(error_msg)
            raise ResponseError(
                error_msg,
                provider=provider,
                response_data={"response": response},
            )
        raise
