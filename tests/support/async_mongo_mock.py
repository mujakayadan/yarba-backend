"""In-memory MongoDB mock compatible with PyMongo AsyncMongoClient (Beanie 2.x tests)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import mongomock

_MONGOMOCK_KWARGS_SKIP = frozenset(
    {
        "authorizedCollections",
        "comment",
        "nameOnly",
        "maxTimeMS",
        "readPreference",
        "session",
    }
)

_CLIENT_KWARGS_SKIP = frozenset(
    {
        "io_loop",
        "maxPoolSize",
        "minPoolSize",
        "maxIdleTimeMS",
        "serverSelectionTimeoutMS",
        "connectTimeoutMS",
        "socketTimeoutMS",
        "retryWrites",
        "retryReads",
    }
)


def _filter_client_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value for key, value in kwargs.items() if key not in _CLIENT_KWARGS_SKIP
    }


def _filter_mongomock_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value for key, value in kwargs.items() if key not in _MONGOMOCK_KWARGS_SKIP
    }


async def _run_sync(func, /, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)


class AsyncMongoMockCursor:
    """Async iterator over a synchronous mongomock cursor."""

    def __init__(self, sync_cursor: Any) -> None:
        self._cursor = sync_cursor

    def __aiter__(self) -> AsyncIterator[Any]:
        return self

    async def __anext__(self) -> Any:
        def _next_item():
            return next(self._cursor)

        try:
            return await _run_sync(_next_item)
        except StopIteration as exc:
            raise StopAsyncIteration from exc

    async def to_list(self, length: int | None = None) -> list[Any]:
        if length is None:
            return await _run_sync(list, self._cursor)
        return await _run_sync(self._cursor.to_list, length)


class AsyncMongoMockCollection:
    """Collection wrapper exposing async methods Beanie expects."""

    def __init__(self, sync_collection: Any) -> None:
        self._collection = sync_collection

    async def insert_one(self, *args: Any, **kwargs: Any) -> Any:
        return await _run_sync(self._collection.insert_one, *args, **kwargs)

    async def insert_many(self, *args: Any, **kwargs: Any) -> Any:
        return await _run_sync(self._collection.insert_many, *args, **kwargs)

    async def find_one(self, *args: Any, **kwargs: Any) -> Any:
        return await _run_sync(self._collection.find_one, *args, **kwargs)

    def find(self, *args: Any, **kwargs: Any) -> AsyncMongoMockCursor:
        return AsyncMongoMockCursor(self._collection.find(*args, **kwargs))

    async def update_one(self, *args: Any, **kwargs: Any) -> Any:
        return await _run_sync(self._collection.update_one, *args, **kwargs)

    async def update_many(self, *args: Any, **kwargs: Any) -> Any:
        return await _run_sync(self._collection.update_many, *args, **kwargs)

    async def replace_one(self, *args: Any, **kwargs: Any) -> Any:
        return await _run_sync(self._collection.replace_one, *args, **kwargs)

    async def delete_one(self, *args: Any, **kwargs: Any) -> Any:
        return await _run_sync(self._collection.delete_one, *args, **kwargs)

    async def delete_many(self, *args: Any, **kwargs: Any) -> Any:
        return await _run_sync(self._collection.delete_many, *args, **kwargs)

    async def count_documents(self, *args: Any, **kwargs: Any) -> int:
        return await _run_sync(self._collection.count_documents, *args, **kwargs)

    async def aggregate(self, *args: Any, **kwargs: Any) -> AsyncMongoMockCursor:
        pipeline = await _run_sync(list, self._collection.aggregate(*args, **kwargs))
        return AsyncMongoMockCursor(iter(pipeline))

    async def create_index(self, *args: Any, **kwargs: Any) -> Any:
        return await _run_sync(self._collection.create_index, *args, **kwargs)

    async def drop(self, *args: Any, **kwargs: Any) -> Any:
        return await _run_sync(self._collection.drop, *args, **kwargs)

    async def drop_indexes(self, *args: Any, **kwargs: Any) -> Any:
        return await _run_sync(self._collection.drop_indexes, *args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._collection, name)
        if not callable(attr):
            return attr

        async def _async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await _run_sync(attr, *args, **kwargs)

        return _async_wrapper


class AsyncMongoMockDatabase:
    """Database wrapper for init_beanie and test cleanup."""

    def __init__(self, sync_database: Any) -> None:
        self._database = sync_database

    def __getitem__(self, name: str) -> AsyncMongoMockCollection:
        return AsyncMongoMockCollection(self._database[name])

    def get_collection(self, name: str) -> AsyncMongoMockCollection:
        return AsyncMongoMockCollection(self._database[name])

    async def list_collection_names(self, *args: Any, **kwargs: Any) -> list[str]:
        return await _run_sync(
            self._database.list_collection_names,
            *args,
            **_filter_mongomock_kwargs(kwargs),
        )

    async def command(self, command: Any, *args: Any, **kwargs: Any) -> Any:
        if isinstance(command, str):
            command_name = command
        elif isinstance(command, dict):
            command_name = next(iter(command), "")
        else:
            command_name = str(command)

        if command_name in {
            "ping",
            "buildInfo",
            "hello",
            "ismaster",
            "isMaster",
            "serverStatus",
            "getParameter",
        }:
            return {
                "ok": 1,
                "version": "6.0.0-mock",
                "maxBsonObjectSize": 16777216,
            }

        return await _run_sync(self._database.command, command, *args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._database, name)
        if not callable(attr):
            return attr

        async def _async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await _run_sync(attr, *args, **kwargs)

        return _async_wrapper


class AsyncMongoMockClient:
    """Drop-in test client for ``pymongo.AsyncMongoClient``."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._client = mongomock.MongoClient(*args, **_filter_client_kwargs(kwargs))

    def __getitem__(self, name: str) -> AsyncMongoMockDatabase:
        return AsyncMongoMockDatabase(self._client[name])

    def get_database(self, name: str) -> AsyncMongoMockDatabase:
        return AsyncMongoMockDatabase(self._client[name])

    @property
    def admin(self) -> AsyncMongoMockDatabase:
        return AsyncMongoMockDatabase(self._client.admin)

    async def close(self) -> None:
        self._client.close()

    async def aclose(self) -> None:
        await self.close()
