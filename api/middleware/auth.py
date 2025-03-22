"""Authentication middleware for FastAPI."""

from typing import Annotated, Dict, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt

from config import get_logger, settings
from core.database.factory import get_user_repository
from core.models.user import User
from core.repositories.user_repository import UserRepository

logger = get_logger(__name__)
security = HTTPBearer(auto_error=False)


async def verify_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict:
    """
    Verify JWT token and return payload.

    Args:
        request: FastAPI request object
        credentials: HTTP Authorization credentials containing the JWT token

    Returns:
        Dict: Token payload containing user information

    Raises:
        HTTPException: If token is invalid or expired
    """
    # Check if credentials are provided
    if credentials is None:
        logger.warning(f"Missing authentication token for {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Decode token
        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.auth.jwt_secret_key.get_secret_value(),
            algorithms=[settings.auth.jwt_algorithm],
        )

        # Log successful token verification
        logger.debug(f"Token verified for user {payload.get('sub')}")
        return payload

    except ExpiredSignatureError:
        # Handle expired token
        logger.warning(f"Expired token used for {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except JWTError as e:
        # Handle invalid token
        logger.warning(f"Invalid token used for {request.url.path}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    payload: Dict = Depends(verify_token),
    user_repo: UserRepository = Depends(get_user_repository),
) -> User:
    """
    Get the current authenticated user.

    Args:
        payload: JWT token payload
        user_repo: User repository

    Returns:
        User: Current authenticated user

    Raises:
        HTTPException: If user not found or inactive
    """
    # Extract user email from token
    email = payload.get("sub")
    if email is None:
        logger.warning("Token payload missing 'sub' claim")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database using the correct repository method
    user = await user_repo.get_by_email(email)
    if user is None:
        logger.warning(f"User with email {email} not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get the current active authenticated user.

    Args:
        current_user: Current authenticated user

    Returns:
        User: Current active user

    Raises:
        HTTPException: If user is not active
    """
    if not current_user.is_active:
        logger.warning(
            f"Inactive user {current_user.email} attempted to access protected resource"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def get_current_active_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Get the current authenticated superuser.

    Args:
        current_user: Current authenticated user

    Returns:
        User: Current authenticated superuser

    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        logger.warning(
            f"Non-superuser {current_user.email} attempted to access admin resource"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    return current_user


# Type aliases for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
CurrentSuperuser = Annotated[User, Depends(get_current_active_superuser)]
