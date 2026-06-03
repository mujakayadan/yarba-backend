"""Tests for database connection."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import core.database.connection as connection


@pytest.fixture(autouse=True)
def reset_connection_globals():
    connection._mongo_client = None
    connection._async_mongo_client = None
    yield
    connection._mongo_client = None
    connection._async_mongo_client = None


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.database.url = "mongodb://localhost:27017"
    settings.database.name = "test_db"
    return settings


@pytest.fixture
def mock_mongo_client():
    client = MagicMock()
    client.get_database = MagicMock(return_value=MagicMock())
    client.close = MagicMock()
    return client


@pytest.fixture
def mock_async_mongo_client():
    client = MagicMock()
    client.__getitem__ = MagicMock(return_value=MagicMock())
    client.close = AsyncMock()
    return client


class TestDatabaseConnection:
    def test_get_database_connection(self, mock_settings, mock_mongo_client):
        with (
            patch("core.database.connection.settings", mock_settings),
            patch("pymongo.MongoClient", return_value=mock_mongo_client) as mock_client,
        ):
            db = connection.get_database_connection()

        mock_client.assert_called_once_with("mongodb://localhost:27017")
        mock_mongo_client.get_database.assert_called_once_with("test_db")
        assert db is not None

    @pytest.mark.asyncio
    async def test_get_async_database_connection_caches_client(
        self, mock_settings, mock_async_mongo_client
    ):
        with (
            patch("core.database.connection.settings", mock_settings),
            patch(
                "core.database.connection.AsyncMongoClient",
                return_value=mock_async_mongo_client,
            ) as mock_client,
        ):
            db1 = await connection.get_async_database_connection()
            db2 = await connection.get_async_database_connection()

        mock_client.assert_called_once_with("mongodb://localhost:27017")
        mock_async_mongo_client.__getitem__.assert_called_with("test_db")
        assert db1 is not None and db2 is not None

    def test_close_database_connection(self, mock_settings, mock_mongo_client):
        with (
            patch("core.database.connection.settings", mock_settings),
            patch("pymongo.MongoClient", return_value=mock_mongo_client),
        ):
            connection.get_database_connection()
            connection.close_database_connection()

        mock_mongo_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_async_database_connection(
        self, mock_settings, mock_async_mongo_client
    ):
        with (
            patch("core.database.connection.settings", mock_settings),
            patch(
                "core.database.connection.AsyncMongoClient",
                return_value=mock_async_mongo_client,
            ),
        ):
            await connection.get_async_database_connection()
            await connection.close_async_database_connection()

        mock_async_mongo_client.close.assert_called_once()
