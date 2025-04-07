"""Authentication schemas."""

import re
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    token_type: str = "bearer"


class FirebaseAuthResponse(BaseModel):
    """Firebase authentication response schema."""

    user: Dict[str, Any]
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, description="User's password")


class FirebaseLoginRequest(BaseModel):
    """Firebase token login request schema."""

    id_token: str = Field(..., description="Firebase ID token")


class RegisterRequest(BaseModel):
    """Register request schema."""

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Username must be between 3 and 50 characters, containing only letters, numbers, dots, underscores and hyphens",
    )
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=64,
        description="Password must be between 8 and 64 characters and contain at least one uppercase letter, one lowercase letter, and one number",
    )
    full_name: str = Field(
        ..., min_length=2, max_length=100, description="User's full name"
    )

    @field_validator("username")
    def validate_username(cls, v: str) -> str:
        """Validate username format.

        Args:
            v: Username to validate

        Returns:
            str: Validated username

        Raises:
            ValueError: If username contains invalid characters
        """
        if not re.match(r"^[a-zA-Z0-9._-]+$", v):
            raise ValueError(
                "Username can only contain letters, numbers, dots, underscores, and hyphens"
            )
        return v.lower()  # Convert to lowercase for consistency

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

    @field_validator("full_name")
    def validate_full_name(cls, v: str) -> str:
        """Validate full name format.

        Args:
            v: Full name to validate

        Returns:
            str: Validated and stripped full name

        Raises:
            ValueError: If full name contains invalid characters
        """
        if not re.match(r"^[a-zA-Z\s\'-]+$", v):
            raise ValueError(
                "Full name can only contain letters, spaces, hyphens, and apostrophes"
            )
        return v.strip()


class PasswordResetRequest(BaseModel):
    """Password reset request schema."""

    email: EmailStr = Field(..., description="User's email address")


class EmailVerificationRequest(BaseModel):
    """Email verification request schema."""

    email: EmailStr = Field(..., description="User's email address")


class UserResponse(BaseModel):
    """User response schema."""

    email: EmailStr
    full_name: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None
