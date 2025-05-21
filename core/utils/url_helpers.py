"""URL helper functions."""

from typing import Optional

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


def get_api_url(path: str, base_url: Optional[str] = None) -> str:
    """Build a full API URL by combining the base URL and path.

    This helper ensures paths are correctly joined even if the
    base URL doesn't end with a slash or the path doesn't start with one.

    Args:
        path: Relative path to append to base URL
        base_url: Optional base URL to use instead of settings.auth.api_base_url

    Returns:
        str: Complete API URL
    """
    # Ensure path starts with / if it doesn't already
    if not path.startswith("/"):
        path = f"/{path}"

    # Use provided base_url or get from settings
    base_url = base_url or settings.auth.api_base_url

    # Remove trailing slash from base URL if present
    if base_url.endswith("/"):
        base_url = base_url[:-1]

    full_url = f"{base_url}{path}"
    logger.debug(f"Built API URL: {full_url}")
    return full_url


def get_auth_callback_url(action: str) -> str:
    """Get the URL for authentication callback actions.

    Args:
        action: The authentication action (verify-email, reset-password)

    Returns:
        str: The callback URL for the specified action
    """
    if action == "verify-email":
        return get_api_url(settings.auth.email_verification_path)
    elif action == "reset-password":
        return get_api_url(settings.auth.password_reset_path)
    else:
        raise ValueError(f"Unknown authentication action: {action}")
