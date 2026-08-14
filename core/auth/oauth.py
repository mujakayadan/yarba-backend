"""Asynchronous Google and Apple ID-token verification."""

import asyncio
import hashlib
import hmac
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from time import monotonic
from typing import Any, Protocol

import aiohttp
import jwt
from jwt import PyJWK
from jwt.exceptions import PyJWTError
from pydantic import EmailStr, TypeAdapter, ValidationError

from core.auth.types import IdentityProvider
from core.exceptions.base import AppException, UnauthorizedException

MAX_JWKS_KEYS = 64
MAX_CACHE_ENTRIES = 8
EMAIL_ADAPTER = TypeAdapter(EmailStr)


class OAuthConfigurationException(AppException):
    """OAuth verification is unavailable because audiences are not configured."""

    def __init__(self) -> None:
        super().__init__(
            message="OAuth provider is not configured",
            status_code=503,
            error_code="oauth_not_configured",
        )


class OAuthVerificationException(UnauthorizedException):
    """Provider ID token verification failed."""

    def __init__(self, message: str = "Invalid provider token") -> None:
        super().__init__(message=message, error_code="invalid_provider_token")


@dataclass(frozen=True, slots=True)
class VerifiedProviderIdentity:
    """Claims safe to pass into Yarba identity resolution."""

    provider: IdentityProvider
    subject: str
    email: str | None
    display_name: str | None = None


class JwksFetcher(Protocol):
    """Async transport abstraction for deterministic verifier tests."""

    async def fetch(self, url: str) -> Mapping[str, Any]:
        """Fetch one JWKS document."""


class AiohttpJwksFetcher:
    """Non-blocking bounded-time JWKS transport."""

    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    async def fetch(self, url: str) -> Mapping[str, Any]:
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                payload: dict[str, Any] = await response.json()
                return payload


@dataclass(slots=True)
class _CacheEntry:
    keys: dict[str, PyJWK]
    expires_at: float


class JwksCache:
    """Small async JWKS cache with bounded entries and TTL."""

    def __init__(
        self,
        fetcher: JwksFetcher,
        *,
        ttl_seconds: int,
        max_entries: int = MAX_CACHE_ENTRIES,
    ) -> None:
        self.fetcher = fetcher
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._entries: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(
        self, url: str, kid: str, *, force_refresh: bool = False
    ) -> PyJWK | None:
        now = monotonic()
        entry = self._entries.get(url)
        if not force_refresh and entry is not None and entry.expires_at > now:
            self._entries.move_to_end(url)
            return entry.keys.get(kid)

        async with self._lock:
            now = monotonic()
            entry = self._entries.get(url)
            if not force_refresh and entry is not None and entry.expires_at > now:
                self._entries.move_to_end(url)
                return entry.keys.get(kid)

            payload = await self.fetcher.fetch(url)
            raw_keys = payload.get("keys")
            if not isinstance(raw_keys, list) or len(raw_keys) > MAX_JWKS_KEYS:
                raise OAuthVerificationException()
            parsed: dict[str, PyJWK] = {}
            for raw_key in raw_keys:
                if not isinstance(raw_key, dict):
                    continue
                key_id = raw_key.get("kid")
                if (
                    isinstance(key_id, str)
                    and raw_key.get("kty") == "RSA"
                    and raw_key.get("alg", "RS256") == "RS256"
                    and raw_key.get("use", "sig") == "sig"
                ):
                    try:
                        parsed[key_id] = PyJWK.from_dict(raw_key)
                    except PyJWTError:
                        continue
            self._entries[url] = _CacheEntry(
                keys=parsed,
                expires_at=now + self.ttl_seconds,
            )
            self._entries.move_to_end(url)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)
            return parsed.get(kid)


class OAuthIdTokenVerifier:
    """Verify Google and Apple ID tokens against official JWKS."""

    def __init__(
        self,
        *,
        cache: JwksCache,
        google_jwks_url: str,
        apple_jwks_url: str,
        google_issuers: frozenset[str],
        apple_issuer: str,
        google_audiences: frozenset[str],
        apple_audiences: frozenset[str],
    ) -> None:
        self.cache = cache
        self.google_jwks_url = google_jwks_url
        self.apple_jwks_url = apple_jwks_url
        self.google_issuers = google_issuers
        self.apple_issuer = apple_issuer
        self.google_audiences = google_audiences
        self.apple_audiences = apple_audiences

    async def verify_google(
        self,
        token: str,
        *,
        expected_nonce_hash: str,
    ) -> VerifiedProviderIdentity:
        claims = await self._verify(
            token,
            jwks_url=self.google_jwks_url,
            issuers=self.google_issuers,
            audiences=self.google_audiences,
        )
        _verify_google_nonce(claims, expected_nonce_hash)
        email_verified = claims.get("email_verified")
        if email_verified not in (True, "true"):
            raise OAuthVerificationException("Google email is not verified")
        return VerifiedProviderIdentity(
            provider=IdentityProvider.GOOGLE,
            subject=_required_subject(claims),
            email=_provider_email(claims, required=True),
        )

    async def verify_apple(
        self,
        token: str,
        *,
        expected_nonce_hash: str,
        display_name: str | None = None,
    ) -> VerifiedProviderIdentity:
        claims = await self._verify(
            token,
            jwks_url=self.apple_jwks_url,
            issuers=frozenset({self.apple_issuer}),
            audiences=self.apple_audiences,
        )
        _verify_apple_nonce(claims, expected_nonce_hash)
        email = claims.get("email")
        if email is not None and claims.get("email_verified") not in (True, "true"):
            raise OAuthVerificationException("Apple email is not verified")
        return VerifiedProviderIdentity(
            provider=IdentityProvider.APPLE,
            subject=_required_subject(claims),
            email=_provider_email(claims, required=False),
            display_name=display_name.strip() if display_name else None,
        )

    async def _verify(
        self,
        token: str,
        *,
        jwks_url: str,
        issuers: frozenset[str],
        audiences: frozenset[str],
    ) -> dict[str, Any]:
        if not audiences or not issuers:
            raise OAuthConfigurationException()
        try:
            header = jwt.get_unverified_header(token)
        except PyJWTError as exc:
            raise OAuthVerificationException() from exc
        if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
            raise OAuthVerificationException()
        kid = header["kid"]
        try:
            key = await self.cache.get(jwks_url, kid)
            if key is None:
                key = await self.cache.get(jwks_url, kid, force_refresh=True)
            if key is None:
                raise OAuthVerificationException()
            claims = jwt.decode(
                token,
                key=key.key,
                algorithms=["RS256"],
                audience=list(audiences),
                options={"require": ["iss", "sub", "aud", "exp", "iat"]},
            )
        except OAuthVerificationException:
            raise
        except (PyJWTError, aiohttp.ClientError, TimeoutError) as exc:
            raise OAuthVerificationException() from exc
        issuer = claims.get("iss")
        if not isinstance(issuer, str) or issuer not in issuers:
            raise OAuthVerificationException()
        _required_subject(claims)
        return dict(claims)


def _required_subject(claims: Mapping[str, Any]) -> str:
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise OAuthVerificationException()
    return subject


def _provider_email(
    claims: Mapping[str, Any],
    *,
    required: bool,
) -> str | None:
    email = claims.get("email")
    if email is None and not required:
        return None
    if not isinstance(email, str):
        raise OAuthVerificationException()
    try:
        return str(EMAIL_ADAPTER.validate_python(email))
    except ValidationError as exc:
        raise OAuthVerificationException() from exc


def _verify_google_nonce(
    claims: Mapping[str, Any],
    expected_nonce_hash: str,
) -> None:
    nonce = claims.get("nonce")
    if not isinstance(nonce, str) or not hmac.compare_digest(
        hashlib.sha256(nonce.encode("utf-8")).hexdigest(),
        expected_nonce_hash,
    ):
        raise OAuthVerificationException("Invalid provider nonce")


def _verify_apple_nonce(
    claims: Mapping[str, Any],
    expected_nonce_hash: str,
) -> None:
    nonce = claims.get("nonce")
    if not isinstance(nonce, str) or not hmac.compare_digest(
        nonce,
        expected_nonce_hash,
    ):
        raise OAuthVerificationException("Invalid provider nonce")
