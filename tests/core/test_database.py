"""Tests for database connection."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ...core.database.connection import (
    close_async_database_connection,
    close_database_connection,
    get_async_database_connection,
    get_database_connection,
)


@pytest.fixture
def mock_mongo_client():
    """Fixture for mocking MongoDB client."""
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=None)
    client.get_database = MagicMock()
    return client


@pytest.fixture
def mock_async_mongo_client():
    """Fixture for mocking async MongoDB client."""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.get_database = AsyncMock()
    return client


class TestDatabaseConnection:
    """Tests for database connection functions."""

    def test_get_database_connection(self, mock_mongo_client):
        """Test getting a database connection."""
        # Arrange
        with patch(
            "pymongo.MongoClient", return_value=mock_mongo_client
        ) as mock_client:
            # Mock environment variables
            with patch.dict(
                "os.environ",
                {"MONGODB_URI": "mongodb://localhost:27017", "MONGODB_DB": "test_db"},
            ):
                # Act
                db = get_database_connection()

                # Assert
                mock_client.assert_called_once_with("mongodb://localhost:27017")
                mock_mongo_client.get_database.assert_called_once_with("test_db")
                assert db is not None

    @pytest.mark.asyncio
    async def test_get_async_database_connection(self, mock_async_mongo_client):
        """Test getting an async database connection."""
        # Arrange
        with patch(
            "motor.motor_asyncio.AsyncIOMotorClient",
            return_value=mock_async_mongo_client,
        ) as mock_client:
            # Mock environment variables
            with patch.dict(
                "os.environ",
                {"MONGODB_URI": "mongodb://localhost:27017", "MONGODB_DB": "test_db"},
            ):
                # Act
                db = await get_async_database_connection()

                # Assert
                mock_client.assert_called_once_with("mongodb://localhost:27017")
                mock_async_mongo_client.get_database.assert_called_once_with("test_db")
                assert db is not None

    def test_close_database_connection(self, mock_mongo_client):
        """Test closing a database connection."""
        # Arrange
        with patch(
            "pymongo.MongoClient", return_value=mock_mongo_client
        ) as mock_client:
            # Mock environment variables
            with patch.dict(
                "os.environ",
                {"MONGODB_URI": "mongodb://localhost:27017", "MONGODB_DB": "test_db"},
            ):
                # Act
                get_database_connection()  # Get a connection first
                close_database_connection()  # Then close it

                # Assert
                mock_client.assert_called_once()
                mock_mongo_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_async_database_connection(self, mock_async_mongo_client):
        """Test closing an async database connection."""
        # Arrange
        with patch(
            "motor.motor_asyncio.AsyncIOMotorClient",
            return_value=mock_async_mongo_client,
        ) as mock_client:
            # Mock environment variables
            with patch.dict(
                "os.environ",
                {"MONGODB_URI": "mongodb://localhost:27017", "MONGODB_DB": "test_db"},
            ):
                # Act
                await get_async_database_connection()  # Get a connection first
                await close_async_database_connection()  # Then close it

                # Assert
                mock_client.assert_called_once()
                mock_async_mongo_client.close.assert_called_once()

    def test_get_database_connection_with_default_values(self, mock_mongo_client):
        """Test getting a database connection with default values."""
        # Arrange
        with patch(
            "pymongo.MongoClient", return_value=mock_mongo_client
        ) as mock_client:
            # Mock environment variables with empty values
            with patch.dict("os.environ", {"MONGODB_URI": "", "MONGODB_DB": ""}):
                # Act
                db = get_database_connection()

                # Assert
                mock_client.assert_called_once_with("mongodb://localhost:27017")
                mock_mongo_client.get_database.assert_called_once_with("resume_builder")
                assert db is not None

    @pytest.mark.asyncio
    async def test_get_async_database_connection_with_default_values(
        self, mock_async_mongo_client
    ):
        """Test getting an async database connection with default values."""
        # Arrange
        with patch(
            "motor.motor_asyncio.AsyncIOMotorClient",
            return_value=mock_async_mongo_client,
        ) as mock_client:
            # Mock environment variables with empty values
            with patch.dict("os.environ", {"MONGODB_URI": "", "MONGODB_DB": ""}):
                # Act
                db = await get_async_database_connection()

                # Assert
                mock_client.assert_called_once_with("mongodb://localhost:27017")
                mock_async_mongo_client.get_database.assert_called_once_with(
                    "resume_builder"
                )
                assert db is not None
