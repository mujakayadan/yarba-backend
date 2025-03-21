"""API schema models package."""

from .auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from .resume import (
    CoverLetterCreate,
    CoverLetterResponse,
    ResumeCreate,
    ResumeFilter,
    ResumeResponse,
    ResumeUpdate,
)

__all__ = [
    # Auth schemas
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "UserResponse",
    # Resume schemas
    "ResumeCreate",
    "ResumeUpdate",
    "ResumeFilter",
    "ResumeResponse",
    # Cover letter schemas
    "CoverLetterCreate",
    "CoverLetterResponse",
]
