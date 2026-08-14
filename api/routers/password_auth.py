"""Backend-owned password and refresh-session routes."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse

from api.middleware.auth import CurrentActiveUser
from api.schemas.auth import (
    ActionTokenConfirmRequest,
    ChangePasswordRequest,
    MessageResponse,
    NativeAuthResponse,
    NativeAuthUser,
    PasswordLoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RegisterRequest,
)
from config.logging_config import get_logger
from config.settings import settings
from core.database.factory import get_native_auth_service
from core.services.native_auth_service import NativeAuthResult, NativeAuthService
from core.services.refresh_token_service import RefreshTokenError
from core.utils.object_id import require_object_id

logger = get_logger(__name__)


def require_native_auth_enabled() -> None:
    """Hide native routes until the rollout feature is enabled."""
    if not settings.features.enable_native_auth:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


router = APIRouter(dependencies=[Depends(require_native_auth_enabled)])
RefreshCookie = Annotated[str | None, Cookie(alias=settings.auth.refresh_cookie_name)]


def _user_payload(result: NativeAuthResult) -> NativeAuthUser:
    user = result.user
    return NativeAuthUser(
        id=str(user.id),
        email=user.email,
        username=user.username,
        email_verified=user.email_verified,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        auth_provider=user.auth_provider,
    )


def _response_payload(result: NativeAuthResult) -> NativeAuthResponse:
    return NativeAuthResponse(
        user=_user_payload(result),
        access_token=result.access_token,
        access_token_expires_in=result.access_token_expires_in,
        is_new_user=result.user.is_new_user,
        current_setup_step=result.user.current_setup_step,
        registration_resumed=False,
    )


def _set_refresh_cookie(response: Response, result: NativeAuthResult) -> None:
    expires_at = result.refresh.session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    max_age = max(0, int((expires_at - datetime.now(UTC)).total_seconds()))
    response.set_cookie(
        key=settings.auth.refresh_cookie_name,
        value=result.refresh.token.get_secret_value(),
        max_age=max_age,
        expires=expires_at,
        path=settings.auth.refresh_cookie_path,
        domain=settings.auth.refresh_cookie_domain,
        secure=settings.auth.refresh_cookie_secure,
        httponly=True,
        samesite=settings.auth.refresh_cookie_samesite,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.auth.refresh_cookie_name,
        path=settings.auth.refresh_cookie_path,
        domain=settings.auth.refresh_cookie_domain,
        secure=settings.auth.refresh_cookie_secure,
        httponly=True,
        samesite=settings.auth.refresh_cookie_samesite,
    )


@router.post(
    "/register",
    response_model=NativeAuthResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_password(
    request: RegisterRequest,
    response: Response,
    service: NativeAuthService = Depends(get_native_auth_service),
) -> NativeAuthResponse:
    """Register a native-only account and establish a refresh session."""
    result = await service.register(request.email, request.password)
    _set_refresh_cookie(response, result)
    return _response_payload(result)


@router.post("/login", response_model=NativeAuthResponse)
async def login_password(
    request: PasswordLoginRequest,
    response: Response,
    service: NativeAuthService = Depends(get_native_auth_service),
) -> NativeAuthResponse:
    """Authenticate with a native password and establish a refresh session."""
    result = await service.login(request.email, request.password)
    _set_refresh_cookie(response, result)
    return _response_payload(result)


@router.post("/refresh", response_model=NativeAuthResponse)
async def refresh_password_session(
    response: Response,
    refresh_cookie: RefreshCookie = None,
    service: NativeAuthService = Depends(get_native_auth_service),
) -> NativeAuthResponse | JSONResponse:
    """Rotate the cookie refresh token and return a new access token."""
    if not refresh_cookie:
        error_response = JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid session"},
        )
        _clear_refresh_cookie(error_response)
        return error_response
    try:
        result = await service.refresh(refresh_cookie)
    except RefreshTokenError:
        error_response = JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid session"},
        )
        _clear_refresh_cookie(error_response)
        return error_response
    _set_refresh_cookie(response, result)
    return _response_payload(result)


@router.post("/logout", response_model=MessageResponse)
async def logout_password_session(
    response: Response,
    refresh_cookie: RefreshCookie = None,
    service: NativeAuthService = Depends(get_native_auth_service),
) -> MessageResponse:
    """Revoke the current refresh family and clear its cookie."""
    if refresh_cookie:
        await service.logout(refresh_cookie)
    _clear_refresh_cookie(response)
    return MessageResponse(message="Logged out")


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all_password_sessions(
    response: Response,
    current_user: CurrentActiveUser,
    service: NativeAuthService = Depends(get_native_auth_service),
) -> MessageResponse:
    """Revoke all refresh families owned by the authenticated user."""
    await service.logout_all(require_object_id(current_user.id))
    _clear_refresh_cookie(response)
    return MessageResponse(message="Logged out from all sessions")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: PasswordResetRequest,
    service: NativeAuthService = Depends(get_native_auth_service),
) -> MessageResponse:
    """Request reset instructions without disclosing account existence."""
    try:
        await service.request_password_reset(request.email)
    except Exception:
        logger.exception("Native password reset email delivery failed")
    return MessageResponse(
        message="If the account is eligible, password reset instructions were sent"
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: PasswordResetConfirmRequest,
    response: Response,
    service: NativeAuthService = Depends(get_native_auth_service),
) -> MessageResponse:
    """Consume a single-use token and set a native password."""
    await service.reset_password(
        request.token.get_secret_value(),
        request.new_password,
    )
    _clear_refresh_cookie(response)
    return MessageResponse(message="Password reset successfully")


@router.post("/request-verification", response_model=MessageResponse)
async def request_verification(
    request: PasswordResetRequest,
    service: NativeAuthService = Depends(get_native_auth_service),
) -> MessageResponse:
    """Request email verification without disclosing account state."""
    try:
        await service.request_verification(request.email)
    except Exception:
        logger.exception("Native verification email delivery failed")
    return MessageResponse(
        message="If the account is eligible, verification instructions were sent"
    )


@router.post("/confirm-verification", response_model=MessageResponse)
async def confirm_verification(
    request: ActionTokenConfirmRequest,
    service: NativeAuthService = Depends(get_native_auth_service),
) -> MessageResponse:
    """Consume a single-use email verification token."""
    await service.confirm_verification(request.token.get_secret_value())
    return MessageResponse(message="Email verified successfully")


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    response: Response,
    current_user: CurrentActiveUser,
    service: NativeAuthService = Depends(get_native_auth_service),
) -> MessageResponse:
    """Change the current native password and revoke refresh sessions."""
    await service.change_password(
        current_user,
        request.current_password,
        request.new_password,
    )
    _clear_refresh_cookie(response)
    return MessageResponse(message="Password changed successfully")


@router.post("/deactivate", response_model=MessageResponse)
async def deactivate_account(
    response: Response,
    current_user: CurrentActiveUser,
    service: NativeAuthService = Depends(get_native_auth_service),
) -> MessageResponse:
    """Soft-deactivate the account; hard deletion is not implemented."""
    await service.deactivate(current_user)
    _clear_refresh_cookie(response)
    return MessageResponse(message="Account deactivated")
