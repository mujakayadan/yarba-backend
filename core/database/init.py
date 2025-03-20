"""Database initialization module.

This module provides functions for initializing the database connection
and setting up the database for the application.
"""

import logging
from typing import Optional

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from config.logging_config import get_logger
from config.settings import Settings
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
        # Create motor client
        client = AsyncIOMotorClient(
            settings.database.url,
            minPoolSize=settings.database.min_pool_size,
            maxPoolSize=settings.database.max_pool_size,
            serverSelectionTimeoutMS=5000,
        )

        # Initialize beanie with all document models
        document_models = [
            # User models
            User,
            # Resume models
            Resume,
            # Profile models
            Profile,
            # Portfolio models
            Portfolio,
            # LaTeX models
            TexHeader,
            Preamble,
        ]

        await init_beanie(
            database=client[settings.database.name],
            document_models=document_models,
        )

        # Test connection
        await client.admin.command("ping")
        logger.info("Successfully initialized database connection")
        return client

    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        return None
