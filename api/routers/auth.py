"""Authentication router."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Dict

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import EmailStr

from config import get_logger, settings
from core.auth.firebase import FirebaseAuth
from core.database import get_unit_of_work
from core.database.factory import get_auth_service, get_firebase_auth_service
from core.database.unit_of_work import AsyncMongoUnitOfWork
from core.models.user import User
from core.services.auth_service import AuthService
from core.services.firebase_auth_service import FirebaseAuthService

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
    """Register a new user.

    Args:
        request: Registration request
        uow: Unit of work
        auth_service: Auth service

    Returns:
        dict: Success message

    Raises:
        HTTPException: If username or email already exists
    """
    if settings.auth.use_firebase_auth:
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
        firebase_service = await anext(get_firebase_auth_service())
        try:
            await firebase_service.register_with_firebase(
                email=request.email,
                password=request.password,
                full_name=request.full_name,
            )
            return {"message": "User registered successfully with Firebase"}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Registration failed: {str(e)}",
            )
    else:
        # Use regular registration logic
        async with uow:
            # Check if username already exists
            existing_user = await uow.user_repository.get_by_username(request.username)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered",
                )

            # Check if email already exists
            existing_email = await uow.user_repository.get_by_email(request.email)
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )

            # Create new user with default values for date fields
            current_time = datetime.now(timezone.utc)
            future_date = current_time + timedelta(
                days=365
            )  # Default expiration 1 year in future

            user = User(
                username=request.username,
                email=request.email,
                hashed_password=User.hash_password(request.password),
                is_active=True,
                is_superuser=False,
                last_login=current_time,
                account_locked_until=current_time,  # Not locked, so current time
                reset_password_token="",  # Empty string instead of None
                reset_password_expires=current_time,
                verification_token="",  # Empty string instead of None
                subscription_expires=future_date,
                last_active=current_time,
            )
            await user.create()

            # Create profile for user
            await uow.profile_repository.create_for_user(
                user=user,
                full_name=request.full_name,
                email=request.email,
            )

        return {"message": "User registered successfully"}


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Login a user with email and password.

    Args:
        form_data: Login form data (username field contains email)
        auth_service: Authentication service

    Returns:
        TokenResponse: Access token and token type

    Raises:
        HTTPException: If email or password is incorrect
    """
    # Use the auth service for login logic, passing username field as email
    result = await auth_service.login(form_data.username, form_data.password)
    return TokenResponse(
        access_token=result["access_token"], token_type=result["token_type"]
    )


@router.post("/firebase/login", response_model=FirebaseAuthResponse)
async def firebase_login(
    request: FirebaseLoginRequest,
    firebase_service: FirebaseAuthService = Depends(get_firebase_auth_service),
) -> FirebaseAuthResponse:
    """Login with Firebase ID token.

    Args:
        request: Firebase login request
        firebase_service: Firebase authentication service

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
        result = await firebase_service.login_with_firebase(request.id_token)
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
    firebase_service: FirebaseAuthService = Depends(get_firebase_auth_service),
) -> Dict[str, str]:
    """Send password reset email.

    Args:
        request: Password reset request
        firebase_service: Firebase authentication service

    Returns:
        Dict: Success message

    Raises:
        HTTPException: If the operation fails
    """
    try:
        await firebase_service.send_password_reset_email(request.email)
        return {"message": "Password reset instructions sent to your email"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to send password reset email: {str(e)}",
        )


@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def send_verification_email(
    request: EmailVerificationRequest,
    firebase_service: FirebaseAuthService = Depends(get_firebase_auth_service),
) -> Dict[str, str]:
    """Send email verification link.

    Args:
        request: Email verification request
        firebase_service: Firebase authentication service

    Returns:
        Dict: Success message

    Raises:
        HTTPException: If the operation fails
    """
    try:
        await firebase_service.send_verification_email(request.email)
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
    """Change user password.

    Args:
        request: Change password request
        current_user: Current authenticated user
        auth_service: Auth service

    Returns:
        Dict: Success message

    Raises:
        HTTPException: If current password is incorrect or operation fails
    """
    # Skip for Firebase users
    if current_user.auth_provider == "firebase":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please use the Firebase change password endpoint for Firebase users",
        )

    # Verify the current password
    if not auth_service.verify_password(
        request.current_password, current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    try:
        # Update user with new password
        update_data = {"password": request.new_password}
        await auth_service.update_user(current_user.id, update_data)

        return {"message": "Password changed successfully"}
    except Exception as e:
        logger.error(f"Failed to change password: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password",
        )


@router.post("/firebase/change-password", status_code=status.HTTP_200_OK)
async def firebase_change_password(
    request: ChangePasswordRequest,
    current_user: CurrentActiveUser,
    firebase_service: FirebaseAuthService = Depends(get_firebase_auth_service),
) -> Dict[str, str]:
    """Change Firebase user password.

    Args:
        request: Change password request
        current_user: Current authenticated user
        firebase_service: Firebase authentication service

    Returns:
        Dict: Success message

    Raises:
        HTTPException: If operation fails
    """
    # Only for Firebase users
    if current_user.auth_provider != "firebase":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please use the regular change password endpoint for non-Firebase users",
        )

    try:
        # Use Firebase to change password
        await firebase_service.change_firebase_password(
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


@router.post("/firebase/verify-token", status_code=status.HTTP_200_OK)
async def verify_firebase_token(
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


@router.post("/firebase/register", response_model=schemas.UserResponse)
async def firebase_register(
    request: schemas.RegisterRequest,
    firebase_auth_service: FirebaseAuthService = Depends(get_firebase_auth_service),
) -> Any:
    """
    Register a new user with Firebase Authentication.
    """
    logger.info(f"Firebase registration request for email: {request.email}")

    try:
        user = await firebase_auth_service.register_with_firebase(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            username=request.username,
        )
        logger.info(f"Firebase registration successful for: {request.email}")
        return user
    except Exception as e:
        logger.error(f"Firebase registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Firebase registration failed: {str(e)}",
        )
