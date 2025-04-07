"""Database initialization module.

This module provides functions for initializing the database connection
and setting up the database for the application.
"""

import os
from typing import Optional

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from config.logging_config import get_logger
from config.settings import Settings
from core.models.cover_letter import CoverLetter
from core.models.portfolio import Portfolio
from core.models.preamble import Preamble
from core.models.profile import Profile
from core.models.resume import Resume
from core.models.tex_header import TexHeader
from core.models.user import User

logger = get_logger(__name__)
settings = Settings()


async def init_db() -> Optional[AsyncIOMotorClient]:
    """Initialize database connection.

    Returns:
        Optional[AsyncIOMotorClient]: Database client if successful, None otherwise.
    """
    try:
        # Debug database connection settings
        mongodb_uri = os.environ.get("MONGODB_URI", settings.database.url)
        mongodb_db = os.environ.get("MONGODB_DATABASE", settings.database.name)

        logger.info(f"Connecting to MongoDB at: {mongodb_uri} (database: {mongodb_db})")

        # Create motor client
        client = AsyncIOMotorClient(
            mongodb_uri,
            minPoolSize=settings.database.min_pool_size,
            maxPoolSize=settings.database.max_pool_size,
            serverSelectionTimeoutMS=10000,  # Increased timeout
        )

        # Initialize beanie with all document models
        document_models = [
            # User models
            User,
            # Resume models
            Resume,
            # Cover letter models
            CoverLetter,
            # Profile models
            Profile,
            # Portfolio models
            Portfolio,
            # LaTeX models
            TexHeader,
            Preamble,
        ]

        # Test connection before initializing Beanie
        logger.info("Testing MongoDB connection...")
        await client.admin.command("ping")
        logger.info("MongoDB connection test successful")

        logger.info(f"Initializing Beanie with database: {mongodb_db}")
        await init_beanie(
            database=client[mongodb_db],
            document_models=document_models,
        )

        logger.info("Successfully initialized database connection and Beanie ODM")
        return client

    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        # Print more details about error
        import traceback

        logger.error(f"Error details: {traceback.format_exc()}")
        return None
