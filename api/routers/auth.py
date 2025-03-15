"""Authentication router."""

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import EmailStr

from config import get_logger, settings

from ...core.models.user import User
from ..dependencies.database import UserRepository
from ..schemas.auth import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter()
logger = get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api.api_prefix}/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    user_repo: UserRepository,
) -> User:
    """Get the current user from the JWT token.

    Args:
        token: JWT token
        user_repo: User repository

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
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError as e:
        logger.warning(f"JWT token validation failed: {e}")
        raise credentials_exception

    # Get user from database
    user = await user_repo.find_one({"email": email})
    if user is None:
        logger.warning(f"User with email {email} not found")
        raise credentials_exception

    return user


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create a new JWT access token.

    Args:
        data: Token data
        expires_delta: Token expiration time

    Returns:
        str: JWT token
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.auth.jwt_access_token_expire_minutes
        )

    to_encode.update({"exp": expire})

    # Create JWT token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.auth.jwt_secret_key.get_secret_value(),
        algorithm=settings.auth.jwt_algorithm,
    )

    return encoded_jwt


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    user_repo: UserRepository,
) -> dict:
    """Register a new user.

    Args:
        request: Registration request
        user_repo: User repository

    Returns:
        dict: Registration result

    Raises:
        HTTPException: If email already exists
    """
    # Check if email already exists
    existing_user = await user_repo.find_one({"email": request.email})
    if existing_user:
        logger.warning(f"Registration attempt with existing email: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user
    from ...core.auth.password import get_password_hash

    user = User(
        email=request.email,
        hashed_password=get_password_hash(request.password),
        full_name=request.full_name,
    )

    # Save user to database
    await user.insert()
    logger.info(f"New user registered: {request.email}")

    return {"message": "User registered successfully"}


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_repo: UserRepository,
) -> TokenResponse:
    """Login a user.

    Args:
        form_data: Login form data
        user_repo: User repository

    Returns:
        TokenResponse: Access token

    Raises:
        HTTPException: If credentials are invalid
    """
    # Get user from database
    user = await user_repo.find_one({"email": form_data.username})
    if not user:
        logger.warning(f"Login attempt with non-existent email: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    from ...core.auth.password import verify_password

    if not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last login
    user.last_login = datetime.utcnow()
    await user.save()

    # Create access token
    access_token = create_access_token(
        data={"sub": user.email},
    )

    logger.info(f"User logged in: {user.email}")
    return TokenResponse(access_token=access_token, token_type="bearer")
