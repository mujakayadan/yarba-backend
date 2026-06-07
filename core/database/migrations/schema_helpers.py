"""Helpers for idempotent MongoDB schema migrations."""

from __future__ import annotations

from typing import Any

from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import CollectionInvalid, OperationFailure


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


def ensure_indexes(collection: Collection[Any], specs: list[Any]) -> None:
    for spec in specs:
        if isinstance(spec, tuple):
            collection.create_index(list(spec))
        else:
            collection.create_index(spec)
