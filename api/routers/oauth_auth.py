"""Direct Google and Apple identity verification routes."""

from typing import Annotated, Literal

from fastapi import APIRouter, Cookie, Depends, Response, status
from fastapi.responses import JSONResponse

from api.routers.password_auth import (
    _response_payload,
    _set_refresh_cookie,
    require_native_auth_enabled,
)
from api.schemas.auth import (
    AppleOAuthRequest,
    GoogleOAuthRequest,
    NativeAuthResponse,
    OAuthNonceResponse,
)
from config.settings import settings
from core.auth.oauth import OAuthIdTokenVerifier, OAuthVerificationException
from core.auth.types import IdentityProvider
from core.database.factory import (
    get_native_auth_service,
    get_oauth_id_token_verifier,
    get_oauth_nonce_service,
)
from core.exceptions.base import AppException
from core.services.native_auth_service import NativeAuthService
from core.services.oauth_nonce_service import (
    InvalidOAuthNonceException,
    OAuthNonceService,
)

router = APIRouter(dependencies=[Depends(require_native_auth_enabled)])
OAuthNonceCookie = Annotated[
    str | None,
    Cookie(alias=settings.auth.oauth_nonce_cookie_name),
]


def _set_nonce_cookie(response: Response, cookie: str) -> None:
    response.set_cookie(
        key=settings.auth.oauth_nonce_cookie_name,
        value=cookie,
        max_age=settings.auth.oauth_nonce_cookie_max_age_seconds,
        path=settings.auth.oauth_nonce_cookie_path,
        secure=settings.auth.oauth_nonce_cookie_secure,
        httponly=True,
        samesite=settings.auth.oauth_nonce_cookie_samesite,
    )


def _clear_nonce_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.auth.oauth_nonce_cookie_name,
        path=settings.auth.oauth_nonce_cookie_path,
        secure=settings.auth.oauth_nonce_cookie_secure,
        httponly=True,
        samesite=settings.auth.oauth_nonce_cookie_samesite,
    )


def _oauth_error_response(exc: AppException) -> JSONResponse:
    is_server_error = exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR
    response = JSONResponse(
        status_code=exc.status_code,
        content={
            "message": (
                "An unexpected error occurred" if is_server_error else exc.message
            ),
            "error_code": exc.error_code,
        },
    )
    _clear_nonce_cookie(response)
    return response


def _oauth_internal_error_response() -> JSONResponse:
    response = JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "message": "An unexpected error occurred",
            "error_code": "internal_server_error",
        },
    )
    _clear_nonce_cookie(response)
    return response


@router.post("/nonce/{provider}", response_model=OAuthNonceResponse)
async def issue_oauth_nonce(
    provider: Literal["google", "apple"],
    response: Response,
    nonce_service: OAuthNonceService = Depends(get_oauth_nonce_service),
) -> OAuthNonceResponse:
    """Issue a raw SDK nonce bound to a signed, single-use HttpOnly cookie.

    Google receives the raw nonce. Apple receives SHA-256(raw nonce) encoded as
    lowercase hexadecimal, while this endpoint's raw value remains client-side.
    """
    issued = await nonce_service.issue(IdentityProvider(provider))
    _set_nonce_cookie(response, issued.cookie.get_secret_value())
    return OAuthNonceResponse(
        nonce=issued.nonce.get_secret_value(),
        expires_in=issued.expires_in,
    )


@router.post("/google", response_model=NativeAuthResponse)
async def authenticate_google(
    request: GoogleOAuthRequest,
    response: Response,
    nonce_cookie: OAuthNonceCookie = None,
    verifier: OAuthIdTokenVerifier = Depends(get_oauth_id_token_verifier),
    nonce_service: OAuthNonceService = Depends(get_oauth_nonce_service),
    service: NativeAuthService = Depends(get_native_auth_service),
) -> NativeAuthResponse | JSONResponse:
    """Verify a Google ID token and establish a Yarba session."""
    try:
        nonce_hash = await nonce_service.consume(
            nonce_cookie or "",
            IdentityProvider.GOOGLE,
        )
        verified = await verifier.verify_google(
            request.id_token.get_secret_value(),
            expected_nonce_hash=nonce_hash,
        )
        result = await service.oauth_login(verified)
    except (InvalidOAuthNonceException, OAuthVerificationException):
        return _oauth_error_response(InvalidOAuthNonceException())
    except AppException as exc:
        return _oauth_error_response(exc)
    except Exception:
        return _oauth_internal_error_response()
    _clear_nonce_cookie(response)
    _set_refresh_cookie(response, result)
    return _response_payload(result)


@router.post("/apple", response_model=NativeAuthResponse)
async def authenticate_apple(
    request: AppleOAuthRequest,
    response: Response,
    nonce_cookie: OAuthNonceCookie = None,
    verifier: OAuthIdTokenVerifier = Depends(get_oauth_id_token_verifier),
    nonce_service: OAuthNonceService = Depends(get_oauth_nonce_service),
    service: NativeAuthService = Depends(get_native_auth_service),
) -> NativeAuthResponse | JSONResponse:
    """Verify an Apple ID token and establish a Yarba session."""
    try:
        nonce_hash = await nonce_service.consume(
            nonce_cookie or "",
            IdentityProvider.APPLE,
        )
        verified = await verifier.verify_apple(
            request.id_token.get_secret_value(),
            expected_nonce_hash=nonce_hash,
            display_name=request.display_name,
        )
        result = await service.oauth_login(verified)
    except (InvalidOAuthNonceException, OAuthVerificationException):
        return _oauth_error_response(InvalidOAuthNonceException())
    except AppException as exc:
        return _oauth_error_response(exc)
    except Exception:
        return _oauth_internal_error_response()
    _clear_nonce_cookie(response)
    _set_refresh_cookie(response, result)
    return _response_payload(result)
