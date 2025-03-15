"""Configuration package.

This package contains all configuration-related modules for the application.
"""

from .constants import (
    API_TAGS_METADATA,
    API_V1_PREFIX,
    APP_CONSTANTS,
    DEFAULT_PAGE_SIZE,
    FEATURE_FLAGS,
    LATEX_COMPILERS,
    LATEX_EXTENSIONS,
    MAX_PAGE_SIZE,
    PDF_EXTENSION,
    PROJECT_ROOT,
    STATIC_DIR,
    TEMPLATES_DIR,
    LLMModel,
    LLMProvider,
    ProcessingMode,
    ResumeSection,
)
from .env_config import (
    ANTHROPIC_API_KEY,
    GEMINI_API_KEY,
    LINKEDIN_EMAIL,
    LINKEDIN_PASSWORD,
    MONGODB_DATABASE,
    MONGODB_URI,
    OLLAMA_URI,
    OPENAI_API_KEY,
    TEST_USER_ID,
)
from .logging_config import configure_logging, get_logger
from .settings import Settings, settings

__all__ = [
    # Constants
    "API_TAGS_METADATA",
    "API_V1_PREFIX",
    "DEFAULT_PAGE_SIZE",
    "LATEX_COMPILERS",
    "LATEX_EXTENSIONS",
    "MAX_PAGE_SIZE",
    "PDF_EXTENSION",
    "PROJECT_ROOT",
    "STATIC_DIR",
    "TEMPLATES_DIR",
    "FEATURE_FLAGS",
    "APP_CONSTANTS",
    "LLMModel",
    "LLMProvider",
    "ProcessingMode",
    "ResumeSection",
    # Environment configuration
    "LINKEDIN_EMAIL",
    "LINKEDIN_PASSWORD",
    "MONGODB_URI",
    "MONGODB_DATABASE",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "OLLAMA_URI",
    "TEST_USER_ID",
    # Logging
    "configure_logging",
    "get_logger",
    # Settings
    "Settings",
    "settings",
]
