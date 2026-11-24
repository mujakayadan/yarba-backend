"""Authentication router."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from config import get_logger
from core.database.factory import get_auth_service
from core.exceptions.base import NotFoundException
from core.services.auth_service import AuthService

from ..middleware.auth import CurrentActiveUser
from ..schemas import auth as schemas

router = APIRouter()
logger = get_logger(__name__)


@router.get("/me", response_model=dict[str, Any])
async def get_current_user_info(current_user: CurrentActiveUser) -> dict[str, Any]:
    """Get current user information.

    Args:
        current_user: Current authenticated active user

    Returns:
        Dict: User information
    """
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "email_verified": current_user.email_verified,
        "auth_provider": current_user.auth_provider,
        "last_login": current_user.last_login,
        "last_active": current_user.last_active,
        "is_new_user": current_user.is_new_user,
        "current_setup_step": current_user.current_setup_step,
    }


@router.put(
    "/users/me/setup-progress", response_model=schemas.UserSetupProgressResponse
)
async def update_setup_progress(
    request: schemas.UpdateSetupProgressRequest,
    current_user: CurrentActiveUser,
    auth_service: AuthService = Depends(get_auth_service),
) -> schemas.UserSetupProgressResponse:
    """Update the current user's setup progress."""
    logger.info(
        f"Updating setup progress for user {current_user.email}: "
        f"Step: {request.current_setup_step}, Completed: {request.setup_completed}"
    )
    try:
        updated_user = await auth_service.update_user_setup_progress(
            user_id=current_user.id,  # type: ignore
            current_setup_step=request.current_setup_step,
            setup_completed=request.setup_completed,
        )
        return schemas.UserSetupProgressResponse(
            id=str(updated_user.id),
            email=updated_user.email,
            is_new_user=updated_user.is_new_user,
            current_setup_step=updated_user.current_setup_step,
            message="User setup progress updated successfully.",
        )
    except NotFoundException as e:
        logger.error(
            f"Error updating setup progress for user {current_user.email}: {e.message}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e.message)
        )
    except Exception as e:
        logger.error(
            f"Unexpected error updating setup progress for {current_user.email}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating setup progress.",
        )
