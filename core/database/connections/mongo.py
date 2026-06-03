"""MongoDB connection manager."""

from pymongo import AsyncMongoClient

from config.logging_config import get_logger
from core.database.types import AsyncMongoClientType, AsyncMongoDatabase

logger = get_logger(__name__)


class MongoDBManager:
    """MongoDB connection manager singleton."""

    _instance: "MongoDBManager | None" = None
    _async_client: AsyncMongoClientType | None = None
    _async_db: AsyncMongoDatabase | None = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, uri: str | None = None, database: str | None = None):
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
    def async_client(self) -> AsyncMongoClientType:
        """Get the async MongoDB client.

        Returns:
            AsyncMongoClient: Async MongoDB client
        """
        if self._async_client is None:
            if not self._uri:
                raise ValueError("MongoDB URI not set. Call initialize() first.")
            self._async_client = AsyncMongoClient(self._uri)
            logger.info("Initialized async MongoDB client")
        return self._async_client

    @property
    def async_db(self) -> AsyncMongoDatabase:
        """Get the async MongoDB database.

        Returns:
            AsyncMongoDatabase: Async MongoDB database
        """
        if self._async_db is None:
            if not self._database:
                raise ValueError("Database name not set. Call initialize() first.")
            self._async_db = self.async_client[self._database]
            logger.info(f"Connected to async MongoDB database: {self._database}")
        return self._async_db

    async def close_async_connection(self) -> None:
        """Close the async MongoDB connection."""
        if self._async_client:
            await self._async_client.close()
            self._async_client = None
            self._async_db = None
            logger.info("Closed async MongoDB connection")


mongo_manager = MongoDBManager()
