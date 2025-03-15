"""Database dependencies for FastAPI."""

from typing import Annotated

from fastapi import Depends

from ...core.models.user import User


async def get_user_repository() -> type[User]:
    """Get the User document model.

    With Beanie, we can use the document models directly
    as repositories with built-in CRUD operations.

    Returns:
        type[User]: User document model class
    """
    return User


# Type alias for dependency injection
UserRepository = Annotated[type[User], Depends(get_user_repository)]

# Add more repository dependencies as needed
