"""Configuration package.

This package contains configuration modules for the application.
"""

from .logging_config import get_logger
from .settings import settings

# Constants
APP_CONSTANTS = {
    "clearance_keywords": [
        "security clearance",
        "clearance required",
        "must be cleared",
        "must have clearance",
        "ts/sci",
        "top secret",
        "secret clearance",
        "public trust",
        "active clearance",
        "current clearance",
        "security+ certification",
    ],
    "extraction_timeout": 30,  # seconds
    "max_retry_attempts": 3,
}

# Feature flags
FEATURE_FLAGS = {
    "check_clearance": True,
    "enable_ai_generation": True,
    "enable_analytics": False,
    "enable_feedback": False,
    "enable_job_extraction": True,
}

__all__ = ["get_logger", "settings", "APP_CONSTANTS", "FEATURE_FLAGS"]
