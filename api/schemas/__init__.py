"""API schema models package."""

from .auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from .cover_letter import (
    CoverLetterCreate,
    CoverLetterFilter,
    CoverLetterResponse,
    CoverLetterUpdate,
    PaginatedCoverLetterResponse,
)
from .resume import (
    PaginatedResumeResponse,
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
    "PaginatedResumeResponse",
    # Cover letter schemas
    "CoverLetterCreate",
    "CoverLetterUpdate",
    "CoverLetterFilter",
    "CoverLetterResponse",
    "PaginatedCoverLetterResponse",
]
