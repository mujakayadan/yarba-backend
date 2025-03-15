"""LLM-related error classes."""

from typing import Optional


class LLMError(Exception):
    """Base exception class for LLM-related errors."""

    def __init__(self, message: str, provider: Optional[str] = None):
        """
        Initialize the error.

        Args:
            message: Error message
            provider: Optional LLM provider name
        """
        self.provider = provider
        super().__init__(message if not provider else f"[{provider}] {message}")


class APIError(LLMError):
    """Exception raised when an API request fails."""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        status_code: Optional[int] = None,
    ):
        """
        Initialize the API error.

        Args:
            message: Error message
            provider: Optional LLM provider name
            status_code: Optional HTTP status code
        """
        self.status_code = status_code
        error_msg = message
        if status_code:
            error_msg = f"{message} (Status: {status_code})"
        super().__init__(error_msg, provider)


class ConfigurationError(LLMError):
    """Exception raised when there's a configuration issue."""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        config_key: Optional[str] = None,
    ):
        """
        Initialize the configuration error.

        Args:
            message: Error message
            provider: Optional LLM provider name
            config_key: Optional configuration key that caused the error
        """
        self.config_key = config_key
        error_msg = message
        if config_key:
            error_msg = f"{message} (Key: {config_key})"
        super().__init__(error_msg, provider)


class ResponseError(LLMError):
    """Exception raised when there's an issue with the API response."""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        response_data: Optional[dict] = None,
    ):
        """
        Initialize the response error.

        Args:
            message: Error message
            provider: Optional LLM provider name
            response_data: Optional response data that caused the error
        """
        self.response_data = response_data
        error_msg = message
        if response_data:
            error_msg = f"{message} (Data: {response_data})"
        super().__init__(error_msg, provider)


class TokenLimitError(LLMError):
    """Exception raised when token limits are exceeded."""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        token_count: Optional[int] = None,
        token_limit: Optional[int] = None,
    ):
        """
        Initialize the token limit error.

        Args:
            message: Error message
            provider: Optional LLM provider name
            token_count: Optional actual token count
            token_limit: Optional token limit
        """
        self.token_count = token_count
        self.token_limit = token_limit
        error_msg = message
        if token_count and token_limit:
            error_msg = f"{message} (Count: {token_count}, Limit: {token_limit})"
        super().__init__(error_msg, provider)
