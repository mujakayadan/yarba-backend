"""API and service tests for backend-owned password authentication."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from fastapi import status
from httpx import AsyncClient

from api.main import app as fastapi_app
from config.settings import settings
from core.auth.types import AuthMigrationState, IdentityProvider
from core.database.factory import get_native_auth_service
from core.exceptions.base import BadRequestException
from core.models.auth_action_token import AuthActionPurpose, AuthActionToken
from core.models.auth_identity import AuthIdentity
from core.models.refresh_token_session import RefreshTokenSession
from core.models.user import User
from core.services.email_clients.resend_client import ResendClient
from core.services.native_auth_service import NativeAuthService
from core.utils.auth_action_token import hash_auth_action_token
from core.utils.object_id import require_object_id

PASSWORD = "NativePassword123"
NEW_PASSWORD = "ChangedPassword123"


@pytest.fixture
def native_auth_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings.features, "enable_native_auth", True)
    monkeypatch.setattr(settings.auth, "refresh_cookie_secure", False)


@pytest.fixture
def native_service_override(native_auth_enabled: None) -> NativeAuthService:
    service = NativeAuthService(resend_client=None)
    fastapi_app.dependency_overrides[get_native_auth_service] = lambda: service
    yield service
    fastapi_app.dependency_overrides.pop(get_native_auth_service, None)


async def _register(client: AsyncClient, email: str = "native@example.com"):
    return await client.post(
        "/api/v1/auth/password/register",
        json={"email": email, "password": PASSWORD},
    )


@pytest.mark.asyncio
async def test_native_routes_are_disabled_by_default(async_client: AsyncClient) -> None:
    response = await _register(async_client)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_native_registration_sets_secure_cookie_contract(
    async_client: AsyncClient,
    native_service_override: NativeAuthService,
) -> None:
    response = await _register(async_client)

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["access_token_expires_in"] == 900
    assert body["is_new_user"] is True
    assert body["current_setup_step"] == 1
    assert body["registration_resumed"] is False
    assert "refresh_token" not in body
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert f"Path={settings.auth.refresh_cookie_path}" in cookie

    user = await User.find_one({"email": "native@example.com"})
    assert user is not None
    assert user.firebase_uid is None
    assert user.auth_migration_state is AuthMigrationState.NATIVE
    identity = await AuthIdentity.find_one({"user_id": user.id})
    assert identity is not None
    assert identity.provider is IdentityProvider.PASSWORD
    assert identity.provider_subject == str(user.id)

    payload = jwt.decode(
        body["access_token"],
        settings.auth.jwt_secret_key.get_secret_value(),
        algorithms=[settings.auth.jwt_algorithm],
    )
    lifetime = payload["exp"] - int(datetime.now(UTC).timestamp())
    assert 895 <= lifetime <= 900


@pytest.mark.asyncio
async def test_uppercase_registration_persists_canonical_email_and_logs_in(
    async_client: AsyncClient,
    native_service_override: NativeAuthService,
) -> None:
    registered = await _register(async_client, "Upper.Native@Example.COM")
    assert registered.status_code == status.HTTP_201_CREATED
    assert registered.json()["user"]["email"] == "upper.native@example.com"

    user = await User.find_one({"email": "upper.native@example.com"})
    assert user is not None
    identity = await AuthIdentity.find_one({"user_id": user.id})
    assert identity is not None
    assert identity.provider_email == "upper.native@example.com"

    login = await async_client.post(
        "/api/v1/auth/password/login",
        json={"email": "UPPER.NATIVE@EXAMPLE.COM", "password": PASSWORD},
    )
    assert login.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_case_variant_native_registration_conflicts(
    async_client: AsyncClient,
    native_service_override: NativeAuthService,
) -> None:
    first = await _register(async_client, "case.variant@example.com")
    duplicate = await _register(async_client, "CASE.VARIANT@EXAMPLE.COM")

    assert first.status_code == status.HTTP_201_CREATED
    assert duplicate.status_code == status.HTTP_409_CONFLICT
    assert await User.find({"email": "case.variant@example.com"}).count() == 1


@pytest.mark.asyncio
async def test_registration_conflict_does_not_claim_existing_email(
    async_client: AsyncClient,
    native_service_override: NativeAuthService,
    test_user: User,
) -> None:
    response = await _register(async_client, str(test_user.email))
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "unavailable" in response.json()["message"].lower()
    unchanged = await User.get(test_user.id)
    assert unchanged is not None
    assert unchanged.password_hash is None


@pytest.mark.asyncio
async def test_password_login_and_wrong_password_are_generic(
    async_client: AsyncClient,
    native_service_override: NativeAuthService,
) -> None:
    await _register(async_client)
    success = await async_client.post(
        "/api/v1/auth/password/login",
        json={"email": "native@example.com", "password": PASSWORD},
    )
    wrong = await async_client.post(
        "/api/v1/auth/password/login",
        json={"email": "native@example.com", "password": "WrongPassword123"},
    )
    missing = await async_client.post(
        "/api/v1/auth/password/login",
        json={"email": "missing@example.com", "password": "WrongPassword123"},
    )

    assert success.status_code == status.HTTP_200_OK
    assert wrong.status_code == status.HTTP_401_UNAUTHORIZED
    assert missing.status_code == status.HTTP_401_UNAUTHORIZED
    assert wrong.json()["message"] == missing.json()["message"]


@pytest.mark.asyncio
async def test_refresh_rotates_cookie_and_reuse_revokes_family(
    async_client: AsyncClient,
    native_service_override: NativeAuthService,
) -> None:
    registered = await _register(async_client)
    original = registered.cookies[settings.auth.refresh_cookie_name]

    refreshed = await async_client.post("/api/v1/auth/password/refresh")
    replacement = refreshed.cookies[settings.auth.refresh_cookie_name]
    assert refreshed.status_code == status.HTTP_200_OK
    assert replacement != original

    async_client.cookies.set(
        settings.auth.refresh_cookie_name,
        original,
        path=settings.auth.refresh_cookie_path,
    )
    reused = await async_client.post("/api/v1/auth/password/refresh")
    assert reused.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Max-Age=0" in reused.headers["set-cookie"]

    session = await RefreshTokenSession.find_one({"used_token_hashes": {"$ne": []}})
    assert session is not None
    assert session.reuse_detected_at is not None
    assert session.revoked_at is not None


@pytest.mark.asyncio
async def test_logout_and_logout_all_revoke_sessions(
    async_client: AsyncClient,
    native_service_override: NativeAuthService,
    test_user: User,
) -> None:
    await _register(async_client)
    logout = await async_client.post("/api/v1/auth/password/logout")
    assert logout.status_code == status.HTTP_200_OK
    assert "Max-Age=0" in logout.headers["set-cookie"]

    native_user = await User.find_one({"email": "native@example.com"})
    assert native_user is not None
    native_session = await RefreshTokenSession.find_one({"user_id": native_user.id})
    assert native_session is not None
    assert native_session.revocation_reason == "logout"

    await native_service_override.refresh_tokens.create_session(
        user_id=require_object_id(test_user.id)
    )
    logout_all = await async_client.post("/api/v1/auth/password/logout-all")
    assert logout_all.status_code == status.HTTP_200_OK
    test_session = await RefreshTokenSession.find_one({"user_id": test_user.id})
    assert test_session is not None
    assert test_session.revocation_reason == "logout_all"


@pytest.mark.asyncio
async def test_reset_token_is_hashed_single_use_and_supports_migration(
    beanie_db,
    test_user: User,
) -> None:
    service = NativeAuthService(resend_client=None)
    test_user.email = "Legacy.Mixed@Example.COM"
    await test_user.save()
    await service.refresh_tokens.create_session(user_id=require_object_id(test_user.id))
    issued = await service.issue_action_token(
        user_id=require_object_id(test_user.id),
        purpose=AuthActionPurpose.PASSWORD_RESET,
        lifetime=timedelta(minutes=30),
    )
    raw = issued.get_secret_value()
    stored = await AuthActionToken.find_one({"user_id": test_user.id})
    assert stored is not None
    assert stored.token_hash == hash_auth_action_token(raw)
    assert raw not in repr(stored)

    user = await service.reset_password(raw, NEW_PASSWORD)
    assert user.password_hash is not None
    assert user.auth_migration_state is AuthMigrationState.DUAL
    identity = await AuthIdentity.find_one({"user_id": test_user.id})
    assert identity is not None
    assert identity.provider_email == "legacy.mixed@example.com"
    session = await RefreshTokenSession.find_one({"user_id": test_user.id})
    assert session is not None
    assert session.revocation_reason == "password_reset"

    with pytest.raises(BadRequestException):
        await service.reset_password(raw, NEW_PASSWORD)


@pytest.mark.asyncio
async def test_action_token_expiry_and_email_verification(
    beanie_db,
    test_user: User,
) -> None:
    service = NativeAuthService(resend_client=None)
    test_user.email_verified = False
    await test_user.save()
    now = datetime.now(UTC)
    expired = await service.issue_action_token(
        user_id=require_object_id(test_user.id),
        purpose=AuthActionPurpose.PASSWORD_RESET,
        lifetime=timedelta(days=1),
        now=now,
    )
    consumed = await service.action_tokens.consume(
        token_hash=hash_auth_action_token(expired.get_secret_value()),
        purpose=AuthActionPurpose.PASSWORD_RESET,
        now=now + timedelta(days=2),
    )
    assert consumed is None

    verification = await service.issue_action_token(
        user_id=require_object_id(test_user.id),
        purpose=AuthActionPurpose.EMAIL_VERIFICATION,
        lifetime=timedelta(minutes=30),
    )
    verified = await service.confirm_verification(verification.get_secret_value())
    assert verified.email_verified is True
    with pytest.raises(BadRequestException):
        await service.confirm_verification(verification.get_secret_value())


@pytest.mark.asyncio
async def test_verification_email_uses_hashed_single_use_token(
    beanie_db,
    test_user: User,
) -> None:
    resend = AsyncMock(spec=ResendClient)
    service = NativeAuthService(resend_client=resend)
    test_user.email_verified = False
    await test_user.save()

    await service.request_verification(test_user.email)

    resend.send_email.assert_awaited_once()
    text = resend.send_email.await_args.kwargs["text"]
    link = text.split("Verify email: ", maxsplit=1)[1].splitlines()[0]
    raw_token = parse_qs(urlparse(link).query)["token"][0]
    stored = await AuthActionToken.find_one({"user_id": test_user.id})
    assert stored is not None
    assert stored.token_hash == hash_auth_action_token(raw_token)
    assert raw_token not in repr(stored)


@pytest.mark.asyncio
async def test_change_password_revokes_sessions(
    beanie_db,
    test_user: User,
) -> None:
    service = NativeAuthService(resend_client=None)
    setup = await service.issue_action_token(
        user_id=require_object_id(test_user.id),
        purpose=AuthActionPurpose.PASSWORD_RESET,
        lifetime=timedelta(minutes=30),
    )
    await service.reset_password(setup.get_secret_value(), PASSWORD)
    await service.refresh_tokens.create_session(user_id=require_object_id(test_user.id))

    updated_user = await User.get(test_user.id)
    assert updated_user is not None
    await service.change_password(updated_user, PASSWORD, NEW_PASSWORD)
    session = await RefreshTokenSession.find_one({"user_id": test_user.id})
    assert session is not None
    assert session.revocation_reason == "password_changed"


@pytest.mark.asyncio
async def test_reset_and_verification_endpoint_wiring(
    async_client: AsyncClient,
    native_service_override: NativeAuthService,
    test_user: User,
) -> None:
    test_user.email_verified = False
    await test_user.save()
    verification = await native_service_override.issue_action_token(
        user_id=require_object_id(test_user.id),
        purpose=AuthActionPurpose.EMAIL_VERIFICATION,
        lifetime=timedelta(minutes=30),
    )
    verified = await async_client.post(
        "/api/v1/auth/password/confirm-verification",
        json={"token": verification.get_secret_value()},
    )
    assert verified.status_code == status.HTTP_200_OK

    reset = await native_service_override.issue_action_token(
        user_id=require_object_id(test_user.id),
        purpose=AuthActionPurpose.PASSWORD_RESET,
        lifetime=timedelta(minutes=30),
    )
    reset_response = await async_client.post(
        "/api/v1/auth/password/reset-password",
        json={
            "token": reset.get_secret_value(),
            "new_password": NEW_PASSWORD,
        },
    )
    assert reset_response.status_code == status.HTTP_200_OK

    login = await async_client.post(
        "/api/v1/auth/password/login",
        json={"email": str(test_user.email), "password": NEW_PASSWORD},
    )
    assert login.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_enumeration_safe_request_responses(
    async_client: AsyncClient,
    native_service_override: NativeAuthService,
) -> None:
    await _register(async_client)
    existing = await async_client.post(
        "/api/v1/auth/password/forgot-password",
        json={"email": "native@example.com"},
    )
    missing = await async_client.post(
        "/api/v1/auth/password/forgot-password",
        json={"email": "missing@example.com"},
    )
    verify_missing = await async_client.post(
        "/api/v1/auth/password/request-verification",
        json={"email": "missing@example.com"},
    )
    assert existing.status_code == missing.status_code == status.HTTP_200_OK
    assert existing.json() == missing.json()
    assert verify_missing.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_account_endpoint_uses_soft_deactivation_only(
    async_client: AsyncClient,
    native_service_override: NativeAuthService,
    test_user: User,
) -> None:
    await native_service_override.refresh_tokens.create_session(
        user_id=require_object_id(test_user.id)
    )
    response = await async_client.post("/api/v1/auth/password/deactivate")

    assert response.status_code == status.HTTP_200_OK
    deactivated = await User.get(test_user.id)
    assert deactivated is not None
    assert deactivated.is_active is False
    session = await RefreshTokenSession.find_one({"user_id": test_user.id})
    assert session is not None
    assert session.revocation_reason == "account_deactivated"
