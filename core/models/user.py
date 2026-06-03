"""User model for MongoDB using Beanie ODM."""

from datetime import UTC, datetime
from typing import Annotated

from beanie import Document, Indexed, PydanticObjectId
from pydantic import EmailStr, Field

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
        description="Tracks the current step the user is on in the setup process (1-indexed).",
    )

    # Firebase auth fields (required for authentication)
    firebase_uid: Annotated[str, Indexed()]

    # Firebase supports multiple authentication providers
    auth_provider: str = Field(
        default="firebase.password",
        description="Authentication provider used through Firebase. Examples: "
        "firebase.password, firebase.google, firebase.facebook, firebase.twitter, etc.",
    )

    # Authentication fields
    last_login: datetime | None = None

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
