"""User model for MongoDB using Beanie ODM."""

from datetime import UTC, datetime
from typing import Annotated

from beanie import Document, Indexed, PydanticObjectId
from pydantic import EmailStr, Field

from core.auth.types import AuthMigrationState
from core.models.document_config import BSON_DATETIME_ENCODERS, DOCUMENT_MODEL_CONFIG


class User(Document):
    """User model for MongoDB using Beanie ODM."""

    username: Annotated[str, Indexed(unique=True)]
    email: Annotated[EmailStr, Indexed(unique=True)]
    is_active: bool = True
    is_superuser: bool = False
    email_verified: bool = False
    is_new_user: bool = Field(
        default=True,
        description="Flag to indicate if the user is new and needs to complete the setup flow.",
    )
    current_setup_step: int = Field(
        default=1,
        description="Tracks the current setup step (1-indexed); 0 means setup is complete.",
    )

    firebase_uid: Annotated[str | None, Indexed()] = None
    auth_provider: str = Field(
        default="password",
        description=(
            "Sign-in provider for the account, such as password, google, or apple."
        ),
    )
    password_hash: str | None = Field(default=None, repr=False)
    # Documents that omit this field load as FIREBASE_ONLY. New accounts are NATIVE.
    auth_migration_state: AuthMigrationState = AuthMigrationState.FIREBASE_ONLY
    last_login: datetime | None = None
    moderation_strike_count: int = 0
    copyright_strike_count: int = 0
    repeat_infringer: bool = False

    # Subscription fields
    subscription_status: str = "free"  # free, basic, premium
    subscription_expires: datetime | None = None

    # LinkedIn integration fields
    linkedin_email: str | None = None
    linkedin_integration_enabled: bool = False
    linkedin_last_login: datetime | None = None
    linkedin_auth_token: str | None = None  # For OAuth/session token if available

    # Tracking fields
    last_active: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = DOCUMENT_MODEL_CONFIG

    class Settings:
        """Beanie document settings."""

        name = "users"
        use_state_management = True
        bson_encoders = BSON_DATETIME_ENCODERS


class AuthenticatedUser(User):
    """User loaded from the database; always has a persisted ``id``."""

    id: PydanticObjectId
