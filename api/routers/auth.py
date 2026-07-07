"""Authentication router."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from config import get_logger
from core.database.factory import get_auth_service
from core.exceptions.base import NotFoundException
from core.services.auth_service import AuthService

from ..middleware.auth import CurrentActiveUser
from ..schemas import auth as schemas
from ..schemas.auth import (
    ChangePasswordRequest,
    EmailVerificationRequest,
    FirebaseAuthResponse,
    FirebaseLoginRequest,
    PasswordResetRequest,
    RegisterRequest,
)

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=FirebaseAuthResponse,
)
async def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> FirebaseAuthResponse:
    """Register a new user and return user info and access token.

    Args:
        request: Registration request (containing email and password)
        auth_service: Authentication service

    Returns:
        FirebaseAuthResponse: User data and access token

    Raises:
        HTTPException: If registration fails
    """
    logger.info(
        f"[/register] Received registration request for email: {request.email}"
    )  # Only email and password in request now

    # No username or full_name handling in the router anymore

    logger.info(
        f"[/register] Calling auth_service.register_with_firebase with email: {request.email}"
    )
    try:
        registration_result = await auth_service.register_with_firebase(
            email=request.email,
            password=request.password,
            # full_name and username are no longer passed from here
        )
        logger.info(
            f"[/register] auth_service.register_with_firebase call successful for email: {request.email}"
        )
        # Construct FirebaseAuthResponse from the dictionary returned by the service
        return FirebaseAuthResponse(**registration_result)
    except HTTPException as e:  # Catch FastAPI/Starlette HTTPExceptions directly
        logger.error(
            f"[/register] HTTPException during registration for {request.email}: {e.detail}",
            exc_info=True,
        )
        raise


@router.post("/login", response_model=FirebaseAuthResponse)
async def login(
    request: FirebaseLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> FirebaseAuthResponse:
    """Login with Firebase ID token.

    This endpoint expects a Firebase ID token that is generated after successful
    authentication with Firebase Authentication. We no longer support direct
    username/password authentication.

    Args:
        request: Firebase login request containing the ID token
        auth_service: Authentication service

    Returns:
        FirebaseAuthResponse: User data and access token

    Raises:
        HTTPException: If token is invalid
    """
    try:
        # Log token info for debugging (only first 10 chars for security)
        token_preview = (
            request.id_token[:10] + "..."
            if len(request.id_token) > 10
            else request.id_token
        )
        logger.debug(f"Received Firebase login request with token: {token_preview}")

        # Verify and process Firebase token
        result = await auth_service.login_with_firebase(request.id_token)
        logger.info(
            f"Firebase login successful for user: {result.get('user', {}).get('email')}"
        )
        return FirebaseAuthResponse(**result)
    except Exception as e:
        logger.error(f"Firebase authentication failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Firebase authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    request: PasswordResetRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    """Send password reset email.

    Args:
        request: Password reset request
        auth_service: Authentication service

    Returns:
        Dict: Success message

    Raises:
        HTTPException: If the operation fails
    """
    try:
        await auth_service.send_password_reset_email(request.email)
        return {"message": "Password reset instructions sent to your email"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to send password reset email: {str(e)}",
        )


@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def send_verification_email(
    request: EmailVerificationRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    """Send email verification link.

    Args:
        request: Email verification request
        auth_service: Authentication service

    Returns:
        Dict: Success message

    Raises:
        HTTPException: If the operation fails
    """
    try:
        await auth_service.send_verification_email(request.email)
        return {"message": "Email verification instructions sent to your email"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to send verification email: {str(e)}",
        )


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    request: ChangePasswordRequest,
    current_user: CurrentActiveUser,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    """Change Firebase user password.

    Args:
        request: Change password request
        current_user: Current authenticated user
        auth_service: Authentication service

    Returns:
        Dict: Success message

    Raises:
        HTTPException: If operation fails
    """
    try:
        # Use Firebase to change password
        await auth_service.change_firebase_password(
            current_user.email, request.current_password, request.new_password
        )

        return {"message": "Password changed successfully"}
    except Exception as e:
        logger.error(f"Failed to change Firebase password: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to change password: {str(e)}",
        )


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
