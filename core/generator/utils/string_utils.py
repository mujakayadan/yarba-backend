"""String utilities for the generator package."""

import re
from typing import Any, Optional

from config.logging_config import get_logger
from utils.text import clean_text

logger = get_logger(__name__)


def ensure_string(value: Any, default: str = "") -> str:
    """
    Ensure a value is converted to a string.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        str: String representation of the value
    """
    if value is None:
        return default

    try:
        return str(value)
    except Exception as e:
        logger.warning(f"Failed to convert value to string: {e}")
        return default


def sanitize_filename(filename: str, max_length: Optional[int] = 255) -> str:
    """
    Sanitize a filename by removing invalid characters and limiting length.

    Args:
        filename: Filename to sanitize
        max_length: Maximum length for the filename

    Returns:
        str: Sanitized filename
    """
    if not filename:
        return ""

    # Clean and normalize the text
    filename = clean_text(filename)

    # Replace invalid characters with underscores
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)

    # Remove leading/trailing periods and spaces
    filename = filename.strip(". ")

    # Limit length if specified
    if max_length and len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        max_name_length = max_length - len(ext)
        filename = name[:max_name_length] + ext

    return filename
