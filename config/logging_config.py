"""Logging configuration module."""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Dict, Optional

from .settings import settings


def configure_logging() -> None:
    """Configure logging for the application."""
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.logging.log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatters
    formatter = logging.Formatter(settings.logging.log_format)

    # Console handler
    if settings.logging.log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler
    if settings.logging.log_to_file and settings.logging.log_file:
        # Create log directory if it doesn't exist
        log_dir = Path(settings.logging.log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            settings.logging.log_file,
            maxBytes=settings.logging.log_file_max_size,
            backupCount=settings.logging.log_file_backup_count,
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Set specific log levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)

    # Log configuration complete
    logging.info(f"Logging configured with level {settings.logging.log_level}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    Args:
        name: Logger name

    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)
