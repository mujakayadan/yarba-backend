"""Text processing utilities for the Resume Builder application."""

import re
from typing import Optional

from config.logging_config import get_logger

logger = get_logger(__name__)


def clean_text(text: str, preserve_newlines: bool = False) -> str:
    """
    Clean text by removing extra whitespace and normalizing line endings.

    Args:
        text: Text to clean
        preserve_newlines: Whether to preserve newline characters

    Returns:
        str: Cleaned text
    """
    if not text:
        return ""

    # Replace multiple spaces with a single space
    text = re.sub(
        r"\s+",
        " " if not preserve_newlines else lambda m: "\n" if "\n" in m.group() else " ",
        text,
    )

    # Remove leading/trailing whitespace
    text = text.strip()

    return text


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text by replacing all whitespace sequences with a single space.

    Args:
        text: Text to normalize

    Returns:
        str: Text with normalized whitespace
    """
    if not text:
        return ""

    # Replace all whitespace sequences (including newlines) with a single space
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def remove_special_chars(
    text: str, keep_chars: Optional[str] = None, replacement: str = ""
) -> str:
    """
    Remove special characters from text, optionally keeping specified characters.

    Args:
        text: Text to process
        keep_chars: String of characters to keep (e.g. ".-_")
        replacement: String to replace special characters with

    Returns:
        str: Text with special characters removed
    """
    if not text:
        return ""

    # Build the pattern
    pattern = r"[^a-zA-Z0-9"
    if keep_chars:
        pattern += re.escape(keep_chars)
    pattern += r"]"

    # Replace special characters
    return re.sub(pattern, replacement, text)


def sanitize_mongodb_uri(uri: str) -> str:
    """
    Sanitize a MongoDB URI by removing credentials.

    Args:
        uri: The URI to sanitize

    Returns:
        str: Sanitized URI
    """
    if not uri:
        return ""
    # Replace credentials in MongoDB URI with ***
    return re.sub(r"(mongodb(\+srv)?://)[^:]+:[^@]+@", r"\1***:***@", uri)
