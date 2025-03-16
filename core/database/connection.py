"""Database connection management.

This module provides functions for managing database connections.
It supports both synchronous and asynchronous connections to MongoDB.
"""

import os
from typing import Optional

import pymongo
from motor.motor_asyncio import AsyncIOMotorClient

from config.logging_config import get_logger

logger = get_logger(__name__)

# Global connection instances
_mongo_client: Optional[pymongo.MongoClient] = None
_async_mongo_client: Optional[AsyncIOMotorClient] = None


def get_database_connection():
    """Get a synchronous MongoDB database connection.

    Returns:
        pymongo.database.Database: MongoDB database instance
    """
    global _mongo_client

    # Get connection parameters from environment variables
    mongodb_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    mongodb_db = os.environ.get("MONGODB_DATABASE", "rbt")

    # Create client if it doesn't exist
    if _mongo_client is None:
        logger.info(f"Creating new MongoDB connection to {mongodb_uri}")
        _mongo_client = pymongo.MongoClient(mongodb_uri)

    return _mongo_client.get_database(mongodb_db)


async def get_async_database_connection():
    """Get an asynchronous MongoDB database connection.

    Returns:
        motor.motor_asyncio.AsyncIOMotorDatabase: Async MongoDB database instance
    """
    global _async_mongo_client

    # Get connection parameters from environment variables
    mongodb_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    mongodb_db = os.environ.get("MONGODB_DATABASE", "rbt")

    # Create client if it doesn't exist
    if _async_mongo_client is None:
        logger.info(f"Creating new async MongoDB connection to {mongodb_uri}")
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
