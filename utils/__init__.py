"""Common utilities for the Resume Builder application."""

from utils.file import (
    ensure_directory_exists,
    get_temp_path,
    safe_file_read,
    safe_file_write,
)
from utils.text import clean_text, normalize_whitespace, remove_special_chars
from utils.validation import (
    validate_directory_path,
    validate_file_path,
    validate_string_not_empty,
)

__all__ = (
    # File utilities
    "ensure_directory_exists",
    "get_temp_path",
    "safe_file_write",
    "safe_file_read",
    # Text utilities
    "clean_text",
    "normalize_whitespace",
    "remove_special_chars",
    # Validation utilities
    "validate_file_path",
    "validate_directory_path",
    "validate_string_not_empty",
)
