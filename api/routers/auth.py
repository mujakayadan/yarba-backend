"""Authentication router."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import EmailStr

from config import get_logger, settings
from core.database import get_unit_of_work
from core.database.factory import get_auth_service
from core.database.unit_of_work import AsyncMongoUnitOfWork
from core.models.user import User
from core.services.auth_service import AuthService

from ..middleware.auth import CurrentActiveUser, CurrentSuperuser
from ..schemas.auth import RegisterRequest, TokenResponse

router = APIRouter()
logger = get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api.api_prefix}/auth/login")


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    uow: AsyncMongoUnitOfWork = Depends(get_unit_of_work),
) -> dict:
    """Register a new user.

    Args:
        request: Registration request
        uow: Unit of work

    Returns:
        dict: Success message

    Raises:
        HTTPException: If username or email already exists
    """
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
    """Login a user.

    Args:
        form_data: Login form data
        auth_service: Authentication service

    Returns:
        TokenResponse: Access token and token type

    Raises:
        HTTPException: If username or password is incorrect
    """
    # Use the auth service for login logic
    result = await auth_service.login(form_data.username, form_data.password)
    return TokenResponse(
        access_token=result["access_token"], token_type=result["token_type"]
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
        "last_login": current_user.last_login,
        "last_active": current_user.last_active,
    }
