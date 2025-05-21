"""User model for MongoDB using Beanie ODM."""

from datetime import datetime, timezone
from typing import Optional

from beanie import Document
from pydantic import EmailStr, Field


class User(Document):
    """User model for MongoDB using Beanie ODM."""

    username: str = Field(unique=True, index=True)
    email: EmailStr = Field(unique=True, index=True)
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
    firebase_uid: str = Field(index=True)

    # Firebase supports multiple authentication providers
    auth_provider: str = Field(
        default="firebase.password",
        description="Authentication provider used through Firebase. Examples: "
        "firebase.password, firebase.google, firebase.facebook, firebase.twitter, etc.",
    )

    # Authentication fields
    last_login: Optional[datetime] = None

    # Subscription fields
    subscription_status: str = "free"  # free, basic, premium
    subscription_expires: Optional[datetime] = None

    # LinkedIn integration fields
    linkedin_email: Optional[str] = None
    linkedin_integration_enabled: bool = False
    linkedin_last_login: Optional[datetime] = None
    linkedin_auth_token: Optional[str] = None  # For OAuth/session token if available

    # Tracking fields
    last_active: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {
        "validate_assignment": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {
            datetime: lambda x: x.isoformat(),
        },
    }

    class Settings:
        """Beanie document settings."""

        name = "users"
        use_state_management = True
        bson_encoders = {
            datetime: lambda dt: (
                dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
            ),
        }
