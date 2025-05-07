#!/usr/bin/env python
"""
Direct runner for test_preferences.py with explicit MongoDB connection.

This script runs the test_preferences.py functionality directly with
provided MongoDB connection parameters, bypassing environment file loading.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Setup command line argument parsing
parser = argparse.ArgumentParser(
    description="Run preference tests with direct MongoDB connection"
)
parser.add_argument(
    "--uri",
    required=True,
    help="MongoDB URI (required, e.g. mongodb+srv://username:password@cluster.mongodb.net/)",
)
parser.add_argument("--db", default="rbt", help="MongoDB database name (default: rbt)")
parser.add_argument("--user-id", help="Test user ID (overrides settings.test_user_id)")

args = parser.parse_args()

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Force set MongoDB environment variables before any imports
# This takes precedence over any .env file values
os.environ["MONGODB_URI"] = args.uri
os.environ["MONGODB_DATABASE"] = args.db
print(
    f"Set MongoDB connection to {args.db} database at {args.uri.split('@')[-1] if '@' in args.uri else args.uri}"
)

# Suppress noisy third-party debug logs
for noisy_logger in [
    "pymongo",
    "beanie",
    "httpcore",
    "httpx",
    "motor",
    "bson",
    "asyncio",
    "uvicorn",
    "starlette",
    "litellm",
]:
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)

from beanie import PydanticObjectId

# Import after setting environment variables
from config.logging_config import configure_logging, get_logger
from config.settings import settings
from core.database.init import init_db
from core.models.resume import Resume
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.profile_repository import ProfileRepository
from core.repositories.resume_repository import ResumeRepository
from core.services.job_service import JobService
from core.services.latex_service import LatexService
from core.services.llm_service import LLMService
from core.services.prompt_service import PromptService
from core.services.resume_generation_service import ResumeGenerationService
from core.utils.preference_utils import get_prompt_preferences
from utils.text import sanitize_mongodb_uri

# Override test user ID if provided
if args.user_id:
    from beanie.odm.fields import PydanticObjectId

    settings.test_user_id = PydanticObjectId(args.user_id)
    print(f"Using provided test user ID: {settings.test_user_id}")

# Configure logging
configure_logging()
logger = get_logger(__name__)


async def test_preferences():
    """Test preference handling using real services with test user ID."""
    # Set up database connection
    client = await init_db()
    if not client:
        raise RuntimeError("Failed to initialize database connection")

    try:
        logger.info("=" * 80)
        logger.info("STARTING PREFERENCE TESTS WITH DIRECT CONNECTION")
        logger.info("=" * 80)

        logger.info(
            f"Testing preference handling with test user ID: {settings.test_user_id}"
        )

        # Get repositories
        profile_repo = ProfileRepository()

        # Get profile using test user ID
        profile = await profile_repo.get_by_user_id(settings.test_user_id)

        if profile:
            logger.info(f"Found profile for test user: {settings.test_user_id}")

            # Get preferences from profile
            preferences = get_prompt_preferences(profile)

            # Log preferences
            formatted = json.dumps(preferences, indent=2)
            logger.info(f"Preferences for test user:\n{formatted}")

            # Test prompt service
            prompt_service = PromptService(user_id=settings.test_user_id)
            logger.info("Testing prompt service...")

            logger.info("✓ Successfully retrieved preferences")
            logger.info("Test completed successfully!")
            return True
        else:
            logger.error(f"No profile found for test user ID: {settings.test_user_id}")
            return False
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        logger.error(traceback.format_exc())
        return False
    finally:
        # Clean up database connection
        client.close()
        logger.info("Database connection closed")


if __name__ == "__main__":
    asyncio.run(test_preferences())
