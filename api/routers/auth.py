"""Authentication router."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, Field

from config import get_logger, settings
from core.auth.firebase import FirebaseAuth
from core.database import get_unit_of_work
from core.database.factory import get_auth_service
from core.database.unit_of_work import AsyncMongoUnitOfWork
from core.models.user import User
from core.services.auth_service import AuthService

from ..middleware.auth import CurrentActiveUser, CurrentSuperuser
from ..schemas import auth as schemas
from ..schemas.auth import (
    ChangePasswordRequest,
    EmailVerificationRequest,
    FirebaseAuthResponse,
    FirebaseLoginRequest,
    PasswordResetRequest,
    RegisterRequest,
    TokenResponse,
)

router = APIRouter()
logger = get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api.api_prefix}/auth/login")


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    uow: AsyncMongoUnitOfWork = Depends(get_unit_of_work),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """Register a new user using Firebase authentication.

    Args:
        request: Registration request
        uow: Unit of work
        auth_service: Authentication service

    Returns:
        dict: Success message

    Raises:
        HTTPException: If registration fails
    """
    # Handle optional username for Firebase authentication
    if request.username is None:
        # Generate username from email or full name if not provided
        username = request.full_name.lower().replace(" ", "_")
        # Ensure username is unique by adding a timestamp if needed
        existing_user = None
        try:
            async with uow:
                existing_user = await uow.user_repository.get_by_username(username)
        except Exception:
            pass

        if existing_user:
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            username = f"{username}_{timestamp}"

        # Update the request with the generated username
        request.username = username

    # Use Firebase for registration
    try:
        await auth_service.register_with_firebase(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            username=request.username,
        )
        return {"message": "User registered successfully with Firebase"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}",
        )


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
) -> Dict[str, str]:
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
) -> Dict[str, str]:
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
) -> Dict[str, str]:
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


@router.get("/me", response_model=Dict[str, Any])
async def get_current_user_info(current_user: CurrentActiveUser) -> Dict[str, Any]:
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
    }


@router.post("/verify-token", status_code=status.HTTP_200_OK)
async def verify_token(
    request: FirebaseLoginRequest,
) -> Dict[str, Any]:
    """Test endpoint to verify a Firebase token and show its structure.

    This endpoint is for testing purposes only and should be disabled in production.

    Args:
        request: Firebase token request

    Returns:
        Dict: Detailed token information
    """
    try:
        token = request.id_token
        import jwt as pyjwt

        # Log basic token info
        token_preview = token[:10] + "..." if len(token) > 10 else token
        logger.info(f"Verifying token: {token_preview}")

        # First try to decode the token without verification
        result = {
            "token_length": len(token),
            "verification_status": "not_verified",
            "header": None,
            "payload": None,
            "firebase_verification": None,
            "error": None,
        }

        try:
            # Just decode header to check structure
            header = pyjwt.get_unverified_header(token)
            result["header"] = header

            # Decode payload without verification
            decoded = pyjwt.decode(token, options={"verify_signature": False})
            result["payload"] = decoded

            # Now try Firebase verification
            try:
                firebase_decoded = await FirebaseAuth.verify_token(token)
                result["firebase_verification"] = {
                    "status": "success",
                    "uid": firebase_decoded.get("uid"),
                    "email": firebase_decoded.get("email"),
                }
                result["verification_status"] = "verified"
            except Exception as firebase_error:
                result["firebase_verification"] = {
                    "status": "failed",
                    "error": str(firebase_error),
                }

        except Exception as decode_error:
            result["error"] = f"Token decode error: {str(decode_error)}"

        return result
    except Exception as e:
        logger.error(f"Token verification failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token verification failed: {str(e)}",
        )


class SwaggerLoginRequest(BaseModel):
    """Request model for Swagger UI login."""

    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")


@router.post("/swagger-login", status_code=status.HTTP_200_OK)
async def swagger_login(
    request: SwaggerLoginRequest,
) -> Dict[str, str]:
    """Login with email/password and get Firebase ID token for Swagger UI testing.

    This endpoint is for DEVELOPMENT USE ONLY and should be disabled in production.
    It allows testing API endpoints in Swagger UI by providing an ID token.

    Args:
        request: Swagger login request with email and password

    Returns:
        Dict: Firebase ID token to use with /auth/login endpoint

    Raises:
        HTTPException: If login fails
    """
    if not settings.debug:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available in debug mode",
        )

    try:
        # Sign in with email/password
        result = await FirebaseAuth.sign_in_with_email_password(
            request.email, request.password
        )

        # Extract the ID token from the result
        id_token = result.get("idToken")
        if not id_token:
            raise ValueError("No ID token returned from Firebase")

        return {
            "id_token": id_token,
            "message": "Use this ID token with the /auth/login endpoint in Swagger UI",
        }
    except Exception as e:
        logger.error(f"Firebase authentication failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )
