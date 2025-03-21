"""Authentication router."""

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import EmailStr

from config import get_logger, settings
from core.database import get_unit_of_work, get_user_repository
from core.database.unit_of_work import AsyncMongoUnitOfWork
from core.models.user import User
from core.repositories.user_repository import UserRepository

from ..schemas.auth import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter()
logger = get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api.api_prefix}/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_repository: UserRepository = Depends(get_user_repository),
) -> User:
    """Get the current user from the JWT token.

    Args:
        token: JWT token
        user_repository: User repository

    Returns:
        User: Current user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode JWT token
        payload = jwt.decode(
            token,
            settings.auth.jwt_secret_key.get_secret_value(),
            algorithms=[settings.auth.jwt_algorithm],
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Get user from database
    user = await user_repository.get_by_username(username)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get the current active user.

    Args:
        current_user: Current user

    Returns:
        User: Current active user

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create a JWT access token.

    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time

    Returns:
        str: JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.auth.jwt_expiration_minutes
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.auth.jwt_secret_key.get_secret_value(),
        algorithm=settings.auth.jwt_algorithm,
    )
    return encoded_jwt


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

        # Create new user
        user = User(
            username=request.username,
            email=request.email,
            hashed_password=User.hash_password(request.password),
            is_active=True,
            is_superuser=False,
        )
        await user.create()

        # Create profile for user
        await uow.profile_repository.create_for_user(user)

    return {"message": "User registered successfully"}


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_repository: UserRepository = Depends(get_user_repository),
) -> TokenResponse:
    """Login a user.

    Args:
        form_data: Login form data
        user_repository: User repository

    Returns:
        TokenResponse: Access token and token type

    Raises:
        HTTPException: If username or password is incorrect
    """
    # Get user from database
    user = await user_repository.get_by_username(form_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if account is locked
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is locked. Please contact support.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not user.verify_password(form_data.password):
        # Increment login attempts
        await user_repository.increment_login_attempts(user.id)

        # Check if account should be locked
        if user.login_attempts >= settings.auth.max_login_attempts - 1:
            await user_repository.lock_account(user.id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account locked due to too many failed login attempts",
                headers={"WWW-Authenticate": "Bearer"},
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Reset login attempts on successful login
    await user_repository.reset_login_attempts(user.id)

    # Update last login timestamp
    await user_repository.update_last_login(user.id)

    # Create access token
    access_token = create_access_token(data={"sub": user.username})
    return TokenResponse(access_token=access_token, token_type="bearer")
