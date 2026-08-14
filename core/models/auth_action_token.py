"""Single-use native authentication action tokens."""

from datetime import UTC, datetime
from enum import StrEnum

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel

from core.models.document_config import BSON_DATETIME_ENCODERS, DOCUMENT_MODEL_CONFIG


class AuthActionPurpose(StrEnum):
    """Supported one-time authentication actions."""

    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"


class AuthActionToken(Document):
    """Hashed opaque token for one password or verification action."""

    token_hash: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )
    purpose: AuthActionPurpose
    user_id: PydanticObjectId
    expires_at: datetime
    consumed_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = DOCUMENT_MODEL_CONFIG

    class Settings:
        """Beanie document settings."""

        name = "auth_action_tokens"
        indexes = [
            IndexModel([("token_hash", ASCENDING)], unique=True),
            IndexModel([("user_id", ASCENDING), ("purpose", ASCENDING)]),
            IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0),
        ]
        bson_encoders = BSON_DATETIME_ENCODERS
