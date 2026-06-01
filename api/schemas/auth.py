"""Authentication schemas."""

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    token_type: str = "bearer"


class FirebaseAuthResponse(BaseModel):
    """Firebase authentication response schema."""

    user: dict[str, Any]
    access_token: str
    token_type: str = "bearer"
    is_new_user: bool | None = None
    current_setup_step: int | None = None


class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, description="User's password")


class FirebaseLoginRequest(BaseModel):
    """Firebase token login request schema."""

    id_token: str = Field(..., description="Firebase ID token")


class UpdateSetupProgressRequest(BaseModel):
    """Request schema for updating user setup progress."""

    current_setup_step: int | None = Field(
        None, ge=1, description="The setup step number the user has reached."
    )
    setup_completed: bool | None = Field(
        None, description="Set to true if the entire setup process is completed."
    )


class UserSetupProgressResponse(BaseModel):
    """Response schema for user setup progress update."""

    id: str  # Assuming PydanticObjectId will be converted to str
    email: EmailStr
    is_new_user: bool
    current_setup_step: int
    message: str | None = None


class RegisterRequest(BaseModel):
    """Register request schema."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=64,
        description="Password must be between 8 and 64 characters and contain at least one uppercase letter, one lowercase letter, and one number",
    )

    @field_validator("password")
    def validate_password(cls, v: str) -> str:
        """Validate password complexity.

        Args:
            v: Password to validate

        Returns:
            str: Validated password

        Raises:
            ValueError: If password doesn't meet complexity requirements
        """
        if not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d.@$!%*?&#]{8,}$", v):
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, and one number"
            )
        return v


class PasswordResetRequest(BaseModel):
    """Password reset request schema."""

    email: EmailStr = Field(..., description="User's email address")


class EmailVerificationRequest(BaseModel):
    """Email verification request schema."""

    email: EmailStr = Field(..., description="User's email address")


class ChangePasswordRequest(BaseModel):
    """Change password request schema."""

    current_password: str = Field(..., description="User's current password")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=64,
        description="New password must be between 8 and 64 characters and contain at least one uppercase letter, one lowercase letter, and one number",
    )

    @field_validator("new_password")
    def validate_password(cls, v: str) -> str:
        """Validate password complexity.

        Args:
            v: Password to validate

        Returns:
            str: Validated password

        Raises:
            ValueError: If password doesn't meet complexity requirements
        """
        if not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d.@$!%*?&#]{8,}$", v):
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, and one number"
            )
        return v


class UserResponse(BaseModel):
    """User response schema."""

    email: EmailStr
    full_name: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: datetime | None = None
