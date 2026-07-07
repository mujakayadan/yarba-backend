"""Database connection management.

This module provides functions for managing database connections.
It supports both synchronous and asynchronous connections to MongoDB.
"""

import pymongo
from pymongo import AsyncMongoClient

from config.logging_config import get_logger
from config.settings import settings
from core.database.types import AsyncMongoClientType, AsyncMongoDatabase
from utils.text import sanitize_mongodb_uri

logger = get_logger(__name__)

_mongo_client: pymongo.MongoClient | None = None
_async_mongo_client: AsyncMongoClientType | None = None


def get_database_connection():
    """Get a synchronous MongoDB database connection.

    Returns:
        pymongo.database.Database: MongoDB database instance
    """
    global _mongo_client

    mongodb_uri = settings.database.url
    mongodb_db = settings.database.name

    if _mongo_client is None:
        sanitized_uri = sanitize_mongodb_uri(mongodb_uri)
        logger.info(f"Creating new MongoDB connection to {sanitized_uri}")
        _mongo_client = pymongo.MongoClient(mongodb_uri)

    return _mongo_client.get_database(mongodb_db)


async def get_async_database_connection() -> AsyncMongoDatabase:
    """Get an asynchronous MongoDB database connection.

    Returns:
        AsyncMongoDatabase: Async MongoDB database instance
    """
    global _async_mongo_client

    mongodb_uri = settings.database.url
    mongodb_db = settings.database.name

    if _async_mongo_client is None:
        sanitized_uri = sanitize_mongodb_uri(mongodb_uri)
        logger.info(f"Creating new async MongoDB connection to {sanitized_uri}")
        _async_mongo_client = AsyncMongoClient(mongodb_uri)

    return _async_mongo_client[mongodb_db]


def close_database_connection() -> None:
    """Close the synchronous MongoDB connection."""
    global _mongo_client

    if _mongo_client is not None:
        logger.info("Closing MongoDB connection")
        _mongo_client.close()
        _mongo_client = None


async def close_async_database_connection() -> None:
    """Close the asynchronous MongoDB connection."""
    global _async_mongo_client

    if _async_mongo_client is not None:
        logger.info("Closing async MongoDB connection")
        await _async_mongo_client.close()
        _async_mongo_client = None
