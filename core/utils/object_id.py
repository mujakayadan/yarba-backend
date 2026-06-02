"""Helpers for narrowing Beanie document ObjectIds."""

from beanie import PydanticObjectId
from bson import ObjectId

ObjectIdLike = str | PydanticObjectId | ObjectId


def coerce_object_id(value: ObjectIdLike) -> PydanticObjectId:
    """Convert supported ID values to ``PydanticObjectId``."""
    if isinstance(value, PydanticObjectId):
        return value
    return PydanticObjectId(value)


def require_object_id(value: ObjectIdLike | None) -> PydanticObjectId:
    """Return a non-optional ObjectId for a persisted document."""
    if value is None:
        msg = "Expected persisted document to have an id"
        raise ValueError(msg)
    return coerce_object_id(value)
