"""Direct Google and Apple ID-token verification and session tests."""

import asyncio
import hashlib
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import status
from httpx import AsyncClient

from api.main import app as fastapi_app
from api.schemas.legal import LegalAcceptanceRequest
from config.settings import settings
from core.auth.oauth import (
    JwksCache,
    OAuthConfigurationException,
    OAuthIdTokenVerifier,
    OAuthVerificationException,
    VerifiedProviderIdentity,
)
from core.auth.types import IdentityProvider
from core.database.factory import (
    get_native_auth_service,
    get_oauth_id_token_verifier,
    get_oauth_nonce_service,
)
from core.exceptions.base import BadRequestException, ConflictException
from core.models.auth_identity import AuthIdentity
from core.models.oauth_nonce import OAuthNonce
from core.models.user import User
from core.services.native_auth_service import NativeAuthService
from core.services.oauth_nonce_service import (
    InvalidOAuthNonceException,
    OAuthNonceService,
)
from core.utils.object_id import require_object_id

GOOGLE_AUDIENCE = "google-web-client.apps.googleusercontent.com"
APPLE_AUDIENCE = "com.yarba.app"
GOOGLE_ISSUER = "https://accounts.google.com"
APPLE_ISSUER = "https://appleid.apple.com"
GOOGLE_URL = "https://google.test/jwks"
APPLE_URL = "https://apple.test/jwks"
KID = "test-key"
GOOGLE_LEGAL_ACCEPTANCE = {
    "terms_version": "2026-08-19",
    "acceptable_use_version": "2026-08-19",
    "privacy_version": "2026-08-19",
    "ai_data_use_version": "2026-08-19",
    "terms_accepted": True,
    "acceptable_use_accepted": True,
    "privacy_acknowledged": True,
    "ai_data_use_acknowledged": True,
    "minimum_age_confirmed": True,
    "acceptance_surface": "google_oauth",
}
APPLE_LEGAL_ACCEPTANCE = {
    **GOOGLE_LEGAL_ACCEPTANCE,
    "acceptance_surface": "apple_oauth",
}
GOOGLE_LEGAL_ACCEPTANCE_REQUEST = LegalAcceptanceRequest.model_validate(
    GOOGLE_LEGAL_ACCEPTANCE
)


def _nonce_hash(nonce: str) -> str:
    return hashlib.sha256(nonce.encode("utf-8")).hexdigest()


class FakeJwksFetcher:
    """Return local JWKS documents without network access."""

    def __init__(self, documents: Mapping[str, Mapping[str, Any]]) -> None:
        self.documents = documents
        self.calls: list[str] = []

    async def fetch(self, url: str) -> Mapping[str, Any]:
        self.calls.append(url)
        return self.documents[url]


@pytest.fixture
def oauth_keys():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = jwt.algorithms.RSAAlgorithm.to_jwk(
        private_key.public_key(),
        as_dict=True,
    )
    public_jwk.update({"kid": KID, "alg": "RS256", "use": "sig"})
    return private_key, {"keys": [public_jwk]}


@pytest.fixture
def verifier(oauth_keys) -> OAuthIdTokenVerifier:
    _, jwks = oauth_keys
    fetcher = FakeJwksFetcher({GOOGLE_URL: jwks, APPLE_URL: jwks})
    return OAuthIdTokenVerifier(
        cache=JwksCache(fetcher, ttl_seconds=60),
        google_jwks_url=GOOGLE_URL,
        apple_jwks_url=APPLE_URL,
        google_issuers=frozenset({GOOGLE_ISSUER}),
        apple_issuer=APPLE_ISSUER,
        google_audiences=frozenset({GOOGLE_AUDIENCE}),
        apple_audiences=frozenset({APPLE_AUDIENCE}),
    )


def _token(
    private_key,
    *,
    issuer: str,
    audience: str,
    subject: str = "provider-subject",
    email: str | None = "OAuth.User@Example.COM",
    email_verified: bool = True,
    nonce: str | None = "expected-nonce",
    expires_delta: timedelta = timedelta(minutes=5),
    kid: str = KID,
) -> str:
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "iss": issuer,
        "aud": audience,
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    if email is not None:
        claims["email"] = email
        claims["email_verified"] = email_verified
    if nonce is not None:
        claims["nonce"] = nonce
    return jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )


@pytest.mark.asyncio
async def test_verifies_valid_google_and_apple_tokens(
    verifier: OAuthIdTokenVerifier,
    oauth_keys,
) -> None:
    private_key, _ = oauth_keys
    google = await verifier.verify_google(
        _token(
            private_key,
            issuer=GOOGLE_ISSUER,
            audience=GOOGLE_AUDIENCE,
        ),
        expected_nonce_hash=_nonce_hash("expected-nonce"),
    )
    apple = await verifier.verify_apple(
        _token(
            private_key,
            issuer=APPLE_ISSUER,
            audience=APPLE_AUDIENCE,
            email="relay@privaterelay.appleid.com",
            nonce=_nonce_hash("expected-nonce"),
        ),
        expected_nonce_hash=_nonce_hash("expected-nonce"),
        display_name="Example Person",
    )

    assert google.provider is IdentityProvider.GOOGLE
    assert google.email == "OAuth.User@example.com"
    assert apple.provider is IdentityProvider.APPLE
    assert apple.email == "relay@privaterelay.appleid.com"
    assert apple.display_name == "Example Person"


@pytest.mark.asyncio
async def test_rejects_invalid_google_claims_and_signature(
    verifier: OAuthIdTokenVerifier,
    oauth_keys,
) -> None:
    private_key, _ = oauth_keys
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    invalid_tokens = [
        _token(
            other_key,
            issuer=GOOGLE_ISSUER,
            audience=GOOGLE_AUDIENCE,
        ),
        _token(private_key, issuer="https://evil.test", audience=GOOGLE_AUDIENCE),
        _token(private_key, issuer=GOOGLE_ISSUER, audience="wrong-audience"),
        _token(
            private_key,
            issuer=GOOGLE_ISSUER,
            audience=GOOGLE_AUDIENCE,
            expires_delta=timedelta(seconds=-1),
        ),
        _token(
            private_key,
            issuer=GOOGLE_ISSUER,
            audience=GOOGLE_AUDIENCE,
            email_verified=False,
        ),
    ]
    for token in invalid_tokens:
        with pytest.raises(OAuthVerificationException):
            await verifier.verify_google(
                token,
                expected_nonce_hash=_nonce_hash("expected-nonce"),
            )

    valid = _token(
        private_key,
        issuer=GOOGLE_ISSUER,
        audience=GOOGLE_AUDIENCE,
    )
    with pytest.raises(OAuthVerificationException):
        await verifier.verify_google(
            valid,
            expected_nonce_hash=_nonce_hash("wrong-nonce"),
        )

    hs_token = jwt.encode(
        {
            "iss": GOOGLE_ISSUER,
            "aud": GOOGLE_AUDIENCE,
            "sub": "subject",
            "iat": int(datetime.now(UTC).timestamp()),
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
        },
        "symmetric-secret-at-least-32-bytes",
        algorithm="HS256",
        headers={"kid": KID},
    )
    with pytest.raises(OAuthVerificationException):
        await verifier.verify_google(
            hs_token,
            expected_nonce_hash=_nonce_hash("expected-nonce"),
        )


@pytest.mark.asyncio
async def test_unknown_key_forces_one_jwks_refresh(oauth_keys) -> None:
    private_key, jwks = oauth_keys
    fetcher = FakeJwksFetcher({GOOGLE_URL: jwks})
    verifier = OAuthIdTokenVerifier(
        cache=JwksCache(fetcher, ttl_seconds=60),
        google_jwks_url=GOOGLE_URL,
        apple_jwks_url=APPLE_URL,
        google_issuers=frozenset({GOOGLE_ISSUER}),
        apple_issuer=APPLE_ISSUER,
        google_audiences=frozenset({GOOGLE_AUDIENCE}),
        apple_audiences=frozenset({APPLE_AUDIENCE}),
    )
    token = _token(
        private_key,
        issuer=GOOGLE_ISSUER,
        audience=GOOGLE_AUDIENCE,
        kid="unknown-key",
    )

    with pytest.raises(OAuthVerificationException):
        await verifier.verify_google(
            token,
            expected_nonce_hash=_nonce_hash("expected-nonce"),
        )
    assert fetcher.calls == [GOOGLE_URL, GOOGLE_URL]


@pytest.mark.asyncio
async def test_empty_audience_configuration_fails_closed(
    oauth_keys,
) -> None:
    private_key, jwks = oauth_keys
    verifier = OAuthIdTokenVerifier(
        cache=JwksCache(FakeJwksFetcher({GOOGLE_URL: jwks}), ttl_seconds=60),
        google_jwks_url=GOOGLE_URL,
        apple_jwks_url=APPLE_URL,
        google_issuers=frozenset({GOOGLE_ISSUER}),
        apple_issuer=APPLE_ISSUER,
        google_audiences=frozenset(),
        apple_audiences=frozenset(),
    )
    token = _token(
        private_key,
        issuer=GOOGLE_ISSUER,
        audience=GOOGLE_AUDIENCE,
    )

    with pytest.raises(OAuthConfigurationException):
        await verifier.verify_google(
            token,
            expected_nonce_hash=_nonce_hash("expected-nonce"),
        )


@pytest.fixture
def oauth_api(
    monkeypatch: pytest.MonkeyPatch,
    verifier: OAuthIdTokenVerifier,
):
    monkeypatch.setattr(settings.features, "enable_native_auth", True)
    monkeypatch.setattr(settings.auth, "refresh_cookie_secure", False)
    monkeypatch.setattr(settings.auth, "oauth_nonce_cookie_secure", False)
    service = NativeAuthService(resend_client=None)
    nonce_service = OAuthNonceService(
        signing_key="test-oauth-nonce-signing-key",
        lifetime_seconds=600,
    )
    fastapi_app.dependency_overrides[get_native_auth_service] = lambda: service
    fastapi_app.dependency_overrides[get_oauth_id_token_verifier] = lambda: verifier
    fastapi_app.dependency_overrides[get_oauth_nonce_service] = lambda: nonce_service
    yield service
    fastapi_app.dependency_overrides.pop(get_native_auth_service, None)
    fastapi_app.dependency_overrides.pop(get_oauth_id_token_verifier, None)
    fastapi_app.dependency_overrides.pop(get_oauth_nonce_service, None)


async def _issue_nonce(client: AsyncClient, provider: str) -> str:
    response = await client.post(f"/api/v1/auth/oauth/nonce/{provider}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["expires_in"] == 600
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    assert (
        f"Path={settings.auth.oauth_nonce_cookie_path}"
        in response.headers["set-cookie"]
    )
    return response.json()["nonce"]


@pytest.mark.asyncio
async def test_google_endpoint_sets_session_cookie_and_canonical_identity(
    async_client: AsyncClient,
    oauth_api: NativeAuthService,
    oauth_keys,
) -> None:
    private_key, _ = oauth_keys
    nonce = await _issue_nonce(async_client, "google")
    nonce_state = await OAuthNonce.find_one({"consumed_at": None})
    assert nonce_state is not None
    assert nonce_state.nonce_hash == _nonce_hash(nonce)
    assert nonce not in str(nonce_state.model_dump())
    response = await async_client.post(
        "/api/v1/auth/oauth/google",
        json={
            "id_token": _token(
                private_key,
                issuer=GOOGLE_ISSUER,
                audience=GOOGLE_AUDIENCE,
                subject="google-new-user",
                nonce=nonce,
            ),
            "legal_acceptance": GOOGLE_LEGAL_ACCEPTANCE,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["user"]["email"] == "oauth.user@example.com"
    assert body["access_token_expires_in"] == 900
    assert "refresh_token" not in body
    assert "provider_token" not in body
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert f"{settings.auth.oauth_nonce_cookie_name}=" in cookie
    assert "Max-Age=0" in cookie
    identity = await AuthIdentity.find_one(
        {"provider": IdentityProvider.GOOGLE, "provider_subject": "google-new-user"}
    )
    assert identity is not None
    assert identity.provider_email == "oauth.user@example.com"


@pytest.mark.asyncio
async def test_apple_first_and_later_login_without_profile(
    async_client: AsyncClient,
    oauth_api: NativeAuthService,
    oauth_keys,
) -> None:
    private_key, _ = oauth_keys
    first_nonce = await _issue_nonce(async_client, "apple")
    first = await async_client.post(
        "/api/v1/auth/oauth/apple",
        json={
            "id_token": _token(
                private_key,
                issuer=APPLE_ISSUER,
                audience=APPLE_AUDIENCE,
                subject="apple-returning-user",
                email="private@privaterelay.appleid.com",
                nonce=_nonce_hash(first_nonce),
            ),
            "display_name": "Apple Person",
            "legal_acceptance": APPLE_LEGAL_ACCEPTANCE,
        },
    )
    later_nonce = await _issue_nonce(async_client, "apple")
    later = await async_client.post(
        "/api/v1/auth/oauth/apple",
        json={
            "id_token": _token(
                private_key,
                issuer=APPLE_ISSUER,
                audience=APPLE_AUDIENCE,
                subject="apple-returning-user",
                email=None,
                nonce=_nonce_hash(later_nonce),
            )
        },
    )

    assert first.status_code == status.HTTP_200_OK
    assert later.status_code == status.HTTP_200_OK
    assert first.json()["user"]["id"] == later.json()["user"]["id"]
    assert await User.find({"email": "private@privaterelay.appleid.com"}).count() == 1


def _assert_nonce_error(response) -> None:
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["message"] == "Invalid OAuth request"
    cookie = response.headers["set-cookie"]
    assert f"{settings.auth.oauth_nonce_cookie_name}=" in cookie
    assert "Max-Age=0" in cookie


@pytest.mark.asyncio
async def test_missing_tampered_and_wrong_provider_nonce_cookies(
    async_client: AsyncClient,
    oauth_api: NativeAuthService,
    oauth_keys,
) -> None:
    private_key, _ = oauth_keys
    google_token = _token(
        private_key,
        issuer=GOOGLE_ISSUER,
        audience=GOOGLE_AUDIENCE,
        subject="nonce-errors",
    )
    missing = await async_client.post(
        "/api/v1/auth/oauth/google",
        json={"id_token": google_token},
    )
    _assert_nonce_error(missing)

    await _issue_nonce(async_client, "google")
    cookie_name = settings.auth.oauth_nonce_cookie_name
    signed_cookie = async_client.cookies.get(cookie_name)
    assert signed_cookie is not None
    async_client.cookies.set(
        cookie_name,
        f"{signed_cookie}tampered",
        path=settings.auth.oauth_nonce_cookie_path,
    )
    tampered = await async_client.post(
        "/api/v1/auth/oauth/google",
        json={"id_token": google_token},
    )
    _assert_nonce_error(tampered)

    raw_nonce = await _issue_nonce(async_client, "google")
    wrong_provider = await async_client.post(
        "/api/v1/auth/oauth/apple",
        json={
            "id_token": _token(
                private_key,
                issuer=APPLE_ISSUER,
                audience=APPLE_AUDIENCE,
                subject="wrong-provider",
                nonce=_nonce_hash(raw_nonce),
            )
        },
    )
    _assert_nonce_error(wrong_provider)


@pytest.mark.asyncio
async def test_wrong_provider_attempt_atomically_consumes_nonce(beanie_db) -> None:
    service = OAuthNonceService(
        signing_key="test-oauth-nonce-signing-key",
        lifetime_seconds=600,
    )
    issued = await service.issue(IdentityProvider.GOOGLE)

    with pytest.raises(InvalidOAuthNonceException):
        await service.consume(
            issued.cookie.get_secret_value(),
            IdentityProvider.APPLE,
        )

    state = await OAuthNonce.find_one(
        {"nonce_hash": _nonce_hash(issued.nonce.get_secret_value())}
    )
    assert state is not None
    assert state.consumed_at is not None


@pytest.mark.asyncio
async def test_expired_and_replayed_nonce_cookies(
    async_client: AsyncClient,
    oauth_api: NativeAuthService,
    oauth_keys,
) -> None:
    private_key, _ = oauth_keys
    expired_nonce = await _issue_nonce(async_client, "google")
    expired_state = await OAuthNonce.find_one({"consumed_at": None})
    assert expired_state is not None
    await OAuthNonce.get_pymongo_collection().update_one(
        {"_id": expired_state.id},
        {"$set": {"expires_at": datetime.now(UTC) - timedelta(seconds=1)}},
    )
    expired = await async_client.post(
        "/api/v1/auth/oauth/google",
        json={
            "id_token": _token(
                private_key,
                issuer=GOOGLE_ISSUER,
                audience=GOOGLE_AUDIENCE,
                subject="expired-nonce",
                nonce=expired_nonce,
            )
        },
    )
    _assert_nonce_error(expired)

    raw_nonce = await _issue_nonce(async_client, "google")
    cookie_name = settings.auth.oauth_nonce_cookie_name
    signed_cookie = async_client.cookies.get(cookie_name)
    assert signed_cookie is not None
    token = _token(
        private_key,
        issuer=GOOGLE_ISSUER,
        audience=GOOGLE_AUDIENCE,
        subject="replayed-nonce",
        email="replayed.nonce@example.com",
        nonce=raw_nonce,
    )
    success = await async_client.post(
        "/api/v1/auth/oauth/google",
        json={
            "id_token": token,
            "legal_acceptance": GOOGLE_LEGAL_ACCEPTANCE,
        },
    )
    assert success.status_code == status.HTTP_200_OK
    assert "Max-Age=0" in success.headers["set-cookie"]

    async_client.cookies.set(
        cookie_name,
        signed_cookie,
        path=settings.auth.oauth_nonce_cookie_path,
    )
    replayed = await async_client.post(
        "/api/v1/auth/oauth/google",
        json={"id_token": token},
    )
    _assert_nonce_error(replayed)


@pytest.mark.asyncio
async def test_wrong_nonce_claim_consumes_and_clears_cookie(
    async_client: AsyncClient,
    oauth_api: NativeAuthService,
    oauth_keys,
) -> None:
    private_key, _ = oauth_keys
    await _issue_nonce(async_client, "google")
    cookie_name = settings.auth.oauth_nonce_cookie_name
    signed_cookie = async_client.cookies.get(cookie_name)
    assert signed_cookie is not None
    wrong_claim = await async_client.post(
        "/api/v1/auth/oauth/google",
        json={
            "id_token": _token(
                private_key,
                issuer=GOOGLE_ISSUER,
                audience=GOOGLE_AUDIENCE,
                subject="wrong-nonce-claim",
                nonce="attacker-selected",
            )
        },
    )
    _assert_nonce_error(wrong_claim)

    async_client.cookies.set(
        cookie_name,
        signed_cookie,
        path=settings.auth.oauth_nonce_cookie_path,
    )
    replay = await async_client.post(
        "/api/v1/auth/oauth/google",
        json={
            "id_token": _token(
                private_key,
                issuer=GOOGLE_ISSUER,
                audience=GOOGLE_AUDIENCE,
                subject="wrong-nonce-claim",
            )
        },
    )
    _assert_nonce_error(replay)


@pytest.mark.asyncio
async def test_apple_requires_hashed_nonce_and_verified_email(
    async_client: AsyncClient,
    oauth_api: NativeAuthService,
    oauth_keys,
) -> None:
    private_key, _ = oauth_keys
    raw_nonce = await _issue_nonce(async_client, "apple")
    raw_claim = await async_client.post(
        "/api/v1/auth/oauth/apple",
        json={
            "id_token": _token(
                private_key,
                issuer=APPLE_ISSUER,
                audience=APPLE_AUDIENCE,
                subject="apple-raw-nonce",
                email="apple.security@example.com",
                nonce=raw_nonce,
            )
        },
    )
    assert raw_claim.status_code == status.HTTP_401_UNAUTHORIZED

    unverified_nonce = await _issue_nonce(async_client, "apple")
    unverified = await async_client.post(
        "/api/v1/auth/oauth/apple",
        json={
            "id_token": _token(
                private_key,
                issuer=APPLE_ISSUER,
                audience=APPLE_AUDIENCE,
                subject="apple-unverified-email",
                email="apple.unverified@example.com",
                email_verified=False,
                nonce=_nonce_hash(unverified_nonce),
            )
        },
    )
    assert unverified.status_code == status.HTTP_401_UNAUTHORIZED
    assert await User.find_one({"email": "apple.unverified@example.com"}) is None

    verified_nonce = await _issue_nonce(async_client, "apple")
    verified = await async_client.post(
        "/api/v1/auth/oauth/apple",
        json={
            "id_token": _token(
                private_key,
                issuer=APPLE_ISSUER,
                audience=APPLE_AUDIENCE,
                subject="apple-hashed-nonce",
                email="apple.verified@example.com",
                nonce=_nonce_hash(verified_nonce),
            ),
            "legal_acceptance": APPLE_LEGAL_ACCEPTANCE,
        },
    )
    assert verified.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_migrated_identity_resolves_and_unknown_apple_requires_email(
    beanie_db,
    test_user: User,
) -> None:
    service = NativeAuthService(resend_client=None)
    await AuthIdentity(
        user_id=require_object_id(test_user.id),
        provider=IdentityProvider.APPLE,
        provider_subject="migrated-apple",
        provider_email=str(test_user.email).lower(),
    ).insert()

    resolved = await service.oauth_login(
        VerifiedProviderIdentity(
            provider=IdentityProvider.APPLE,
            subject="migrated-apple",
            email=None,
        )
    )
    assert resolved.user.id == test_user.id

    with pytest.raises(BadRequestException) as incomplete:
        await service.oauth_login(
            VerifiedProviderIdentity(
                provider=IdentityProvider.APPLE,
                subject="unknown-apple",
                email=None,
            )
        )
    assert incomplete.value.error_code == "provider_profile_incomplete"


@pytest.mark.asyncio
async def test_unknown_identity_does_not_auto_link_existing_email(
    beanie_db,
    test_user: User,
) -> None:
    service = NativeAuthService(resend_client=None)

    with pytest.raises(ConflictException) as conflict:
        await service.oauth_login(
            VerifiedProviderIdentity(
                provider=IdentityProvider.GOOGLE,
                subject="new-google-subject",
                email=str(test_user.email).upper(),
            ),
            GOOGLE_LEGAL_ACCEPTANCE_REQUEST,
        )
    assert conflict.value.error_code == "account_linking_required"
    assert (
        await AuthIdentity.find_one({"provider_subject": "new-google-subject"}) is None
    )


@pytest.mark.asyncio
async def test_concurrent_provider_requests_resolve_one_user(beanie_db) -> None:
    service = NativeAuthService(resend_client=None)
    verified = VerifiedProviderIdentity(
        provider=IdentityProvider.GOOGLE,
        subject="concurrent-google",
        email="concurrent.oauth@example.com",
    )

    first, second = await asyncio.gather(
        service.oauth_login(verified, GOOGLE_LEGAL_ACCEPTANCE_REQUEST),
        service.oauth_login(verified, GOOGLE_LEGAL_ACCEPTANCE_REQUEST),
    )
    assert first.user.id == second.user.id
    assert await User.find({"email": "concurrent.oauth@example.com"}).count() == 1
    assert (
        await AuthIdentity.find({"provider_subject": "concurrent-google"}).count() == 1
    )


@pytest.mark.asyncio
async def test_oauth_routes_are_disabled_by_default(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings.features, "enable_native_auth", False)
    nonce_response = await async_client.post("/api/v1/auth/oauth/nonce/google")
    response = await async_client.post(
        "/api/v1/auth/oauth/google",
        json={"id_token": "not-used"},
    )
    assert nonce_response.status_code == status.HTTP_404_NOT_FOUND
    assert response.status_code == status.HTTP_404_NOT_FOUND
