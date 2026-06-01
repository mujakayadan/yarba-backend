"""Database connection management.

This module provides functions for managing database connections.
It supports both synchronous and asynchronous connections to MongoDB.
"""

import pymongo
from motor.motor_asyncio import AsyncIOMotorClient

from config.logging_config import get_logger
from config.settings import settings
from utils.text import sanitize_mongodb_uri

logger = get_logger(__name__)

# Global connection instances
_mongo_client: pymongo.MongoClient | None = None
_async_mongo_client: AsyncIOMotorClient | None = None


def get_database_connection():
    """Get a synchronous MongoDB database connection.

    Returns:
        pymongo.database.Database: MongoDB database instance
    """
    global _mongo_client

    # Get connection parameters from settings (which handles environment variables)
    mongodb_uri = settings.database.url
    mongodb_db = settings.database.name

    # Create client if it doesn't exist
    if _mongo_client is None:
        sanitized_uri = sanitize_mongodb_uri(mongodb_uri)
        logger.info(f"Creating new MongoDB connection to {sanitized_uri}")
        _mongo_client = pymongo.MongoClient(mongodb_uri)

    return _mongo_client.get_database(mongodb_db)


async def get_async_database_connection():
    """Get an asynchronous MongoDB database connection.

    Returns:
        motor.motor_asyncio.AsyncIOMotorDatabase: Async MongoDB database instance
    """
    global _async_mongo_client

    # Get connection parameters from settings (which handles environment variables)
    mongodb_uri = settings.database.url
    mongodb_db = settings.database.name

    # Create client if it doesn't exist
    if _async_mongo_client is None:
        sanitized_uri = sanitize_mongodb_uri(mongodb_uri)
        logger.info(f"Creating new async MongoDB connection to {sanitized_uri}")
        _async_mongo_client = AsyncIOMotorClient(mongodb_uri)

    return _async_mongo_client.get_database(mongodb_db)


def close_database_connection():
    """Close the synchronous MongoDB connection."""
    global _mongo_client

    if _mongo_client is not None:
        logger.info("Closing MongoDB connection")
        _mongo_client.close()
        _mongo_client = None


async def close_async_database_connection():
    """Close the asynchronous MongoDB connection."""
    global _async_mongo_client

    if _async_mongo_client is not None:
        logger.info("Closing async MongoDB connection")
        _async_mongo_client.close()
        _async_mongo_client = None
