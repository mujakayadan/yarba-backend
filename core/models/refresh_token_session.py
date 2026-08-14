"""Rotating refresh-token session model."""

from datetime import UTC, datetime

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import ASCENDING, IndexModel

from core.models.document_config import (
    BSON_DATETIME_ENCODERS,
    DOCUMENT_MODEL_CONFIG,
    NESTED_MODEL_CONFIG,
)


class RefreshTokenDeviceMetadata(BaseModel):
    """Optional client metadata captured when a session is created."""

    device_id: str | None = Field(default=None, max_length=255)
    device_name: str | None = Field(default=None, max_length=255)
    user_agent: str | None = Field(default=None, max_length=1024)
    ip_address: str | None = Field(default=None, max_length=64)

    model_config = NESTED_MODEL_CONFIG


class RefreshTokenSession(Document):
    """A refresh-token family with one current token and hashed rotation history."""

    user_id: PydanticObjectId = Field(description="Owner user ID")
    family_id: str = Field(
        min_length=36,
        max_length=36,
        pattern=(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-"
            r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        ),
        description="Stable UUID for this refresh-token family",
    )
    token_hash: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
        description="SHA-256 hash of the current refresh token",
    )
    used_token_hashes: list[str] = Field(
        default_factory=list,
        description="Hashes of previously rotated tokens used for reuse detection",
    )
    expires_at: datetime
    device: RefreshTokenDeviceMetadata | None = None
    rotation_count: int = Field(default=0, ge=0)
    last_used_at: datetime | None = None
    last_rotated_at: datetime | None = None
    revoked_at: datetime | None = None
    revocation_reason: str | None = Field(default=None, max_length=255)
    reuse_detected_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = DOCUMENT_MODEL_CONFIG

    class Settings:
        """Beanie document settings."""

        name = "refresh_token_sessions"
        indexes = [
            IndexModel([("token_hash", ASCENDING)], unique=True),
            IndexModel([("family_id", ASCENDING)], unique=True),
            IndexModel([("user_id", ASCENDING)]),
            IndexModel([("used_token_hashes", ASCENDING)]),
            IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0),
        ]
        bson_encoders = BSON_DATETIME_ENCODERS
