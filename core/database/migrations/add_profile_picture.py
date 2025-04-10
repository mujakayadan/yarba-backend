"""Migration script to add profile_picture field to profiles."""

import asyncio
import os

# Add parent directory to path so we can import project modules
import sys
from pathlib import Path

parent_dir = str(Path(__file__).parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from config.logging_config import configure_logging, get_logger
from config.settings import settings
from core.database.init import init_db
from core.models.profile import Profile

# Configure logging
configure_logging()
logger = get_logger(__name__)


async def migrate_profiles():
    """Add profile_picture field to all profiles."""
    logger.info("Starting migration to add profile_picture field to profiles")

    # Initialize database
    client = await init_db()
    if not client:
        logger.error("Failed to connect to database")
        return

    try:
        # Count profiles
        count = await Profile.count()
        logger.info(f"Found {count} profiles to migrate")

        # Update all profiles to add profile_picture field if it doesn't exist
        result = await Profile.find_all().update(
            {"$set": {"profile_picture": None}},
            ignore_if_set=True,  # Only set if field doesn't exist
        )

        logger.info(
            f"Migration completed successfully. Updated {result.modified_count} profiles."
        )
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
    finally:
        # Close database connection
        client.close()
        logger.info("Database connection closed")


if __name__ == "__main__":
    logger.info("Running profile_picture migration script")
    asyncio.run(migrate_profiles())
    logger.info("Migration script completed")
