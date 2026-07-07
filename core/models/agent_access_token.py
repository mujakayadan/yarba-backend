"""Agent access token model for programmatic (PAT) API access."""

from datetime import UTC, datetime

from beanie import Document, PydanticObjectId
from pydantic import Field

from core.models.document_config import BSON_DATETIME_ENCODERS

VALID_SCOPES: frozenset[str] = frozenset(
    {
        "jobs:extract",
        "resumes:read",
        "resumes:write",
        "cover_letters:read",
        "cover_letters:write",
        "profiles:read",
        "applications:read",
        "applications:write",
        "applications:demographics:read",
        "applications:credentials:read",
    }
)


class AgentAccessToken(Document):
    """Long-lived personal access token that authenticates as its owner.

    Security: a valid token acts as the owning user within its scopes.
    The ``profiles:read`` scope exposes full personal PII to the holder.
    The ``applications:demographics:read`` scope exposes decrypted EEO data.
    The ``applications:credentials:read`` scope exposes the stored careers-site password.
    """

    token_hash: str = Field(description="SHA-256 hash of the raw token")
    user_id: PydanticObjectId = Field(description="Owner user ID")
    label: str = Field(default="", description="Human-readable label")
    scopes: list[str] = Field(default_factory=list, description="Granted scopes")
    is_active: bool = Field(default=True, description="Whether the token is valid")
    expires_at: datetime | None = Field(default=None, description="Optional expiry")
    last_used_at: datetime | None = Field(
        default=None, description="Last successful use timestamp"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "agent_access_tokens"
        indexes = ["token_hash", "user_id"]
        bson_encoders = BSON_DATETIME_ENCODERS
