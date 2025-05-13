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
    ResumeSelectionItem,
    ResumeSelectionList,
    ResumeUpdate,
    SortOptions,
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
    "ResumeSelectionItem",
    "ResumeSelectionList",
    "SortOptions",
    # Cover letter schemas
    "CoverLetterCreate",
    "CoverLetterUpdate",
    "CoverLetterFilter",
    "CoverLetterResponse",
    "PaginatedCoverLetterResponse",
]
