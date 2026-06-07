"""Helpers for idempotent MongoDB schema migrations."""

from __future__ import annotations

from typing import Any

from pymongo import IndexModel
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import CollectionInvalid, OperationFailure


def _index_key(index: dict[str, Any]) -> frozenset[tuple[str, Any]]:
    return frozenset(index["key"].items())


def _has_index(collection: Collection[Any], keys: frozenset[tuple[str, Any]]) -> bool:
    for index in collection.list_indexes():
        if index["name"] == "_id_":
            continue
        if _index_key(index) == keys:
            return True
    return False


def ensure_collection(db: Database[Any], name: str) -> Collection[Any]:
    if name in db.list_collection_names():
        return db[name]
    try:
        return db.create_collection(name)
    except CollectionInvalid:
        return db[name]


def ensure_validator(
    db: Database[Any],
    collection: str,
    validator: dict[str, Any],
    *,
    validation_level: str = "strict",
) -> None:
    try:
        db.command(
            {
                "collMod": collection,
                "validator": validator,
                "validationLevel": validation_level,
            }
        )
    except OperationFailure as exc:
        if exc.code == 8000 and "collMod" in str(exc):
            msg = (
                "MongoDB user lacks collMod permission. Grant dbAdmin on the "
                "database or set MIGRATIONS_MONGODB_URI to an admin connection URI."
            )
            raise RuntimeError(msg) from exc
        raise


def ensure_index_models(collection: Collection[Any], models: list[IndexModel]) -> None:
    for model in models:
        keys = _index_key(model.document)
        if _has_index(collection, keys):
            continue
        try:
            collection.create_indexes([model])
        except OperationFailure as exc:
            # Index exists under the same auto-generated name with different options.
            if exc.code == 86:
                continue
            raise


def ensure_indexes(collection: Collection[Any], specs: list[Any]) -> None:
    for spec in specs:
        if isinstance(spec, tuple):
            keys = frozenset(spec)
        else:
            keys = frozenset([(spec, 1)])
        if _has_index(collection, keys):
            continue
        if isinstance(spec, tuple):
            collection.create_index(list(spec))
        else:
            collection.create_index(spec)
