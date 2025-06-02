"""Database initialization module.

This module provides functions for initializing the database connection
and setting up the database for the application.
"""

from pathlib import Path
from typing import Optional

# Load environment variables from .env files
try:
    from dotenv import load_dotenv

    # Load environment variables from .env.local first, then fallback to others
    env_loaded = False
    for env_file in [".env.local", ".env.production", ".env"]:
        if Path(env_file).exists():
            load_dotenv(dotenv_path=env_file)
            env_loaded = True
            break
except ImportError:
    # dotenv is optional, so handle the case where it's not installed
    pass

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from config.logging_config import get_logger
from config.settings import Settings
from core.models.cover_letter import CoverLetter
from core.models.portfolio import Portfolio
from core.models.portfolio_website import PortfolioWebsite
from core.models.preamble import Preamble
from core.models.profile import Profile
from core.models.resume import Resume
from core.models.tex_header import TexHeader
from core.models.user import User
from utils.text import sanitize_mongodb_uri

logger = get_logger(__name__)
settings = Settings()


async def init_db() -> Optional[AsyncIOMotorClient]:
    """Initialize database connection.

    Returns:
        Optional[AsyncIOMotorClient]: Database client if successful, None otherwise.
    """
    try:
        # Use the database settings which already handle environment variables properly
        mongodb_uri = settings.database.url
        mongodb_db = settings.database.name

        # Log sanitized URI
        sanitized_uri = sanitize_mongodb_uri(mongodb_uri)
        logger.info(
            f"Connecting to MongoDB at: {sanitized_uri} (database: {mongodb_db})"
        )

        if mongodb_uri.startswith("mongodb://localhost"):
            logger.warning(
                "Using a local MongoDB URI. If you intended to connect to a remote database, "
                "make sure the MONGODB_URI environment variable is set in .env.local file."
            )

        # Create motor client using settings
        client = AsyncIOMotorClient(
            mongodb_uri,
            minPoolSize=settings.database.min_pool_size,
            maxPoolSize=settings.database.max_pool_size,
            serverSelectionTimeoutMS=settings.database.server_selection_timeout_ms,
            connectTimeoutMS=settings.database.connection_timeout_ms,
            socketTimeoutMS=settings.database.socket_timeout_ms,
            retryWrites=settings.database.retry_writes,
            retryReads=settings.database.retry_reads,
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
            # Portfolio Website models
            PortfolioWebsite,
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
