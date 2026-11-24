"""Authentication middleware for FastAPI."""

from datetime import UTC, datetime
from typing import Annotated, cast

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import ExpiredSignatureError
from jwt.exceptions import PyJWTError as JWTError

from config import get_logger, settings
from core.database.factory import get_user_repository
from core.models.user import AuthenticatedUser
from core.repositories.agent_access_token_repository import AgentAccessTokenRepository
from core.repositories.user_repository import UserRepository
from core.utils.agent_access_token import TOKEN_PREFIX
from core.utils.object_id import require_object_id

logger = get_logger(__name__)
security = HTTPBearer(auto_error=False)


async def verify_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """Verify a Yarba JWT or agent personal access token.

    Args:
        request: FastAPI request object
        credentials: HTTP Authorization credentials containing the bearer token

    Returns:
        Dict: Token payload containing user information

    Raises:
        HTTPException: If token is invalid or expired
    """
    if credentials is None:
        logger.warning(f"Missing authentication token for {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    if token.startswith(TOKEN_PREFIX):
        repo = AgentAccessTokenRepository()
        record = await repo.get_active_by_raw_token(token)
        if record is None:
            logger.warning(f"Invalid agent token used for {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid agent token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if record.expires_at is not None:
            expires_at = record.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at < datetime.now(UTC):
                logger.warning(f"Expired agent token used for {request.url.path}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Expired agent token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        await repo.touch_last_used(require_object_id(record.id))
        request.state.auth_token_type = "pat"
        request.state.auth_scopes = record.scopes
        logger.debug(f"Agent token verified for user {record.user_id}")
        return {
            "token_type": "pat",
            "user_id": str(record.user_id),
            "scopes": record.scopes,
        }

    try:
        payload = jwt.decode(
            token,
            settings.auth.jwt_secret_key.get_secret_value(),
            algorithms=[settings.auth.jwt_algorithm],
        )
        payload["token_type"] = "jwt"
        request.state.auth_token_type = "jwt"
        request.state.auth_scopes = None
        logger.debug(f"JWT token verified for user {payload.get('sub')}")
        return dict(payload)
    except (JWTError, ExpiredSignatureError) as jwt_error:
        logger.warning(f"Invalid token used for {request.url.path}: {str(jwt_error)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    payload: dict = Depends(verify_token),
    user_repo: UserRepository = Depends(get_user_repository),
) -> AuthenticatedUser:
    """Get the current authenticated user.

    Args:
        payload: JWT or agent-token payload
        user_repo: User repository

    Returns:
        User: Current authenticated user

    Raises:
        HTTPException: If user not found or inactive
    """
    token_type = payload.get("token_type", "jwt")

    if token_type == "pat":
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid agent token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = await user_repo.get_by_id(user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return cast(AuthenticatedUser, user)

    email = payload.get("sub")
    if email is None:
        logger.warning("JWT token payload missing 'sub' claim")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await user_repo.get_by_email(email)
    if user is None:
        logger.warning(f"User with email {email} not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return cast(AuthenticatedUser, user)


async def get_current_active_user(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Get the current active authenticated user.

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
    current_user: AuthenticatedUser = Depends(get_current_active_user),
) -> AuthenticatedUser:
    """Get the current authenticated superuser.

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


def require_scopes(*required: str):
    """Dependency factory: enforce PAT scopes. A human JWT has full access."""

    async def _dep(
        request: Request,
        user: AuthenticatedUser = Depends(get_current_user),
    ) -> AuthenticatedUser:
        token_type = getattr(request.state, "auth_token_type", "jwt")
        if token_type != "pat":
            return user
        granted = set(getattr(request.state, "auth_scopes", []) or [])
        missing = set(required) - granted
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Token missing required scopes: {sorted(missing)}",
            )
        return user

    return _dep


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
CurrentActiveUser = Annotated[AuthenticatedUser, Depends(get_current_active_user)]
CurrentSuperuser = Annotated[AuthenticatedUser, Depends(get_current_active_superuser)]
