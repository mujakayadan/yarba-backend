"""User model for MongoDB using Beanie ODM."""

from datetime import datetime
from typing import List, Optional

from beanie import Document, PydanticObjectId
from pydantic import EmailStr, Field


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

    async def get_profiles(self):
        """Get all profiles for this user."""
        from .profile import Profile

        return await Profile.find(Profile.user_id == self.id).to_list()

    async def get_portfolios(self):
        """Get all portfolios for this user."""
        from .portfolio import Portfolio

        return await Portfolio.find(Portfolio.user_id == self.id).to_list()

    async def get_resumes(self):
        """Get all resumes for this user."""
        from .resume import Resume

        return await Resume.find(Resume.user_id == self.id).to_list()
