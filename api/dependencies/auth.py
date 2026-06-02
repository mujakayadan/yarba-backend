"""Authentication dependencies for FastAPI."""

from typing import Annotated

from fastapi import Depends

from core.models.user import User

from ..middleware.auth import (
    get_current_active_user,
    get_current_user,
)

# Type annotations for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]

__all__ = [
    "CurrentActiveUser",
    "CurrentUser",
    "get_current_active_user",
    "get_current_user",
]
