"""Validation utilities for the Resume Builder application."""

import pathlib
from typing import Union

from config.logging_config import get_logger

logger = get_logger(__name__)


def validate_file_path(file_path: Union[str, pathlib.Path]) -> bool:
    """
    Validate that a file path exists and is a file.

    Args:
        file_path: Path to validate

    Returns:
        bool: True if path is valid, False otherwise
    """
    try:
        path = pathlib.Path(file_path)
        return path.is_file()
    except Exception as e:
        logger.error(f"Error validating file path {file_path}: {str(e)}")
        return False


def validate_directory_path(directory_path: Union[str, pathlib.Path]) -> bool:
    """
    Validate that a directory path exists and is a directory.

    Args:
        directory_path: Path to validate

    Returns:
        bool: True if path is valid, False otherwise
    """
    try:
        path = pathlib.Path(directory_path)
        return path.is_dir()
    except Exception as e:
        logger.error(f"Error validating directory path {directory_path}: {str(e)}")
        return False


def validate_string_not_empty(text: str, trim: bool = True) -> bool:
    """
    Validate that a string is not empty.

    Args:
        text: String to validate
        trim: Whether to trim whitespace before checking

    Returns:
        bool: True if string is not empty, False otherwise
    """
    if not isinstance(text, str):
        return False

    if trim:
        text = text.strip()

    return bool(text)
