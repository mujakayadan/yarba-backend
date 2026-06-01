"""Authentication dependencies for FastAPI."""

from typing import Annotated

from fastapi import Depends

from core.models.user import User

from ..middleware.auth import get_current_active_user

# Type annotation for dependency injection
CurrentUser = Annotated[User, Depends(get_current_active_user)]
