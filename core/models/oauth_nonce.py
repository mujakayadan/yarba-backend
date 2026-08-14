"""Single-use state for backend-issued OAuth nonces."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from beanie import Document, Indexed
from pydantic import Field, StringConstraints
from pymongo import ASCENDING, IndexModel

from core.auth.types import IdentityProvider
from core.models.document_config import BSON_DATETIME_ENCODERS, DOCUMENT_MODEL_CONFIG

Sha256Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
OAuthProvider = Literal[IdentityProvider.GOOGLE, IdentityProvider.APPLE]


class OAuthNonce(Document):
    """Hashed nonce state consumed atomically during OAuth exchange."""

    cookie_hash: Annotated[Sha256Hex, Indexed(unique=True)]
    nonce_hash: Sha256Hex
    provider: OAuthProvider
    expires_at: datetime
    consumed_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = DOCUMENT_MODEL_CONFIG

    class Settings:
        """Beanie document settings."""

        name = "oauth_nonces"
        bson_encoders = BSON_DATETIME_ENCODERS
        indexes = [
            IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0),
            IndexModel([("provider", ASCENDING), ("expires_at", ASCENDING)]),
        ]
