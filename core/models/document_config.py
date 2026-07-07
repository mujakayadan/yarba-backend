"""Shared Pydantic / Beanie configuration for document models."""

from datetime import UTC, datetime
from typing import Any

from pydantic import ConfigDict

DOCUMENT_MODEL_CONFIG = ConfigDict(
    validate_assignment=True,
    arbitrary_types_allowed=True,
)

NESTED_MODEL_CONFIG = ConfigDict(validate_assignment=True)


def encode_datetime_for_bson(dt: datetime) -> datetime:
    """Normalize naive datetimes to UTC before BSON persistence."""
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


BSON_DATETIME_ENCODERS: dict[type[Any], Any] = {datetime: encode_datetime_for_bson}
