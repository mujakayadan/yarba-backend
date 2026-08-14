"""Authentication provider identity linked to a Yarba user."""

from datetime import UTC, datetime

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel

from core.auth.types import IdentityProvider
from core.models.document_config import BSON_DATETIME_ENCODERS, DOCUMENT_MODEL_CONFIG


class AuthIdentity(Document):
    """Provider-owned subject associated with an existing MongoDB user."""

    user_id: PydanticObjectId = Field(description="Linked Yarba user ID")
    provider: IdentityProvider
    provider_subject: str = Field(
        min_length=1,
        max_length=512,
        description="Stable subject identifier asserted by the provider",
    )
    provider_email: str | None = Field(
        default=None,
        description="Provider email snapshot; never used as the identity key",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = DOCUMENT_MODEL_CONFIG

    class Settings:
        """Beanie document settings."""

        name = "auth_identities"
        indexes = [
            IndexModel(
                [("provider", ASCENDING), ("provider_subject", ASCENDING)],
                unique=True,
            ),
            IndexModel([("user_id", ASCENDING)]),
        ]
        bson_encoders = BSON_DATETIME_ENCODERS
