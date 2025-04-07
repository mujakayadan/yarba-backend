"""MongoDB connection manager."""

from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient

from config.logging_config import get_logger

logger = get_logger(__name__)


class MongoDBManager:
    """MongoDB connection manager singleton."""

    _instance: Optional["MongoDBManager"] = None
    _async_client: Optional[AsyncIOMotorClient] = None
    _async_db: Optional[AsyncIOMotorDatabase] = None

    def __new__(cls, *args, **kwargs):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super(MongoDBManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, uri: str = None, database: str = None):
        """Initialize the MongoDB connection manager.

        Args:
            uri: MongoDB connection URI
            database: Database name
        """
        if self._initialized:
            return

        self._uri = uri
        self._database = database
        self._initialized = True

    def initialize(self, uri: str, database: str):
        """Initialize connection parameters.

        Args:
            uri: MongoDB connection URI
            database: Database name
        """
        self._uri = uri
        self._database = database

    @property
    def async_client(self) -> AsyncIOMotorClient:
        """Get the async MongoDB client.

        Returns:
            AsyncIOMotorClient: Async MongoDB client
        """
        if self._async_client is None:
            if not self._uri:
                raise ValueError("MongoDB URI not set. Call initialize() first.")
            self._async_client = AsyncIOMotorClient(self._uri)
            logger.info("Initialized async MongoDB client")
        return self._async_client

    @property
    def async_db(self) -> AsyncIOMotorDatabase:
        """Get the async MongoDB database.

        Returns:
            AsyncIOMotorDatabase: Async MongoDB database
        """
        if self._async_db is None:
            if not self._database:
                raise ValueError("Database name not set. Call initialize() first.")
            self._async_db = self.async_client[self._database]
            logger.info(f"Connected to async MongoDB database: {self._database}")
        return self._async_db

    def close_async_connection(self):
        """Close the async MongoDB connection."""
        if self._async_client:
            self._async_client.close()
            self._async_client = None
            self._async_db = None
            logger.info("Closed async MongoDB connection")


# Global instance
mongo_manager = MongoDBManager()
