"""Authentication dependencies for FastAPI."""

from typing import Annotated

from fastapi import Depends

from core.models.user import AuthenticatedUser

from ..middleware.auth import (
    get_current_active_user,
    get_current_user,
)

# Type annotations for dependency injection
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
CurrentActiveUser = Annotated[AuthenticatedUser, Depends(get_current_active_user)]

__all__ = [
    "AuthenticatedUser",
    "CurrentActiveUser",
    "CurrentUser",
    "get_current_active_user",
    "get_current_user",
]
