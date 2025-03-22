"""User model for MongoDB using Beanie ODM."""

from datetime import datetime
from typing import List, Optional

from beanie import Document, PydanticObjectId
from pydantic import EmailStr, Field

from core.auth.password import get_password_hash, verify_password


class User(Document):
    """User model for MongoDB using Beanie ODM."""

    username: str = Field(unique=True, index=True)
    email: EmailStr = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
    email_verified: bool = False

    # Authentication fields
    last_login: Optional[datetime] = None
    login_attempts: int = 0
    account_locked_until: Optional[datetime] = None
    reset_password_token: Optional[str] = None
    reset_password_expires: Optional[datetime] = None
    verification_token: Optional[str] = None

    # Subscription fields
    subscription_status: str = "free"  # free, basic, premium
    subscription_expires: Optional[datetime] = None

    # Tracking fields
    last_active: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def is_locked(self) -> bool:
        """Check if user account is locked.

        Returns:
            bool: True if account is locked, False otherwise
        """
        return (
            self.account_locked_until is not None
            and self.account_locked_until > datetime.utcnow()
        )

    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hash a password.

        Args:
            password: Plain text password

        Returns:
            str: Hashed password
        """
        return get_password_hash(password)

    def verify_password(self, plain_password: str) -> bool:
        """Verify if the provided password matches the stored hash.

        Args:
            plain_password: Plain text password to verify

        Returns:
            bool: True if password matches, False otherwise
        """
        return verify_password(plain_password, self.hashed_password)

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
            datetime: lambda x: x,
        }
