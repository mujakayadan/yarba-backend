"""Backend-issued, cookie-bound OAuth nonce lifecycle."""

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from pydantic import SecretStr

from core.auth.types import IdentityProvider
from core.exceptions.base import UnauthorizedException
from core.models.oauth_nonce import OAuthNonce, OAuthProvider
from core.repositories.oauth_nonce_repository import OAuthNonceRepository


class InvalidOAuthNonceException(UnauthorizedException):
    """Nonce cookie validation or single-use consumption failed."""

    def __init__(self) -> None:
        super().__init__(
            message="Invalid OAuth request",
            error_code="invalid_oauth_nonce",
        )


@dataclass(frozen=True, slots=True)
class IssuedOAuthNonce:
    """Raw provider nonce plus the separate HttpOnly cookie value."""

    nonce: SecretStr
    cookie: SecretStr
    expires_in: int


class OAuthNonceService:
    """Issue signed nonce cookies and atomically consume persisted state."""

    def __init__(
        self,
        repository: OAuthNonceRepository | None = None,
        *,
        signing_key: str,
        lifetime_seconds: int,
    ) -> None:
        self.repository = repository or OAuthNonceRepository()
        self.signing_key = signing_key.encode("utf-8")
        self.lifetime_seconds = lifetime_seconds

    async def issue(
        self,
        provider: IdentityProvider,
        *,
        now: datetime | None = None,
    ) -> IssuedOAuthNonce:
        """Create a provider-bound nonce without storing its raw value."""
        _require_oauth_provider(provider)
        issued_at = now or datetime.now(UTC)
        expires_at = issued_at + timedelta(seconds=self.lifetime_seconds)
        raw_nonce = secrets.token_urlsafe(32)
        handle = secrets.token_urlsafe(32)
        payload = _encode_payload(
            {
                "provider": provider.value,
                "handle": handle,
                "exp": int(expires_at.timestamp()),
            }
        )
        signature = _sign(payload, self.signing_key)
        cookie = f"{payload}.{signature}"
        await self.repository.create(
            OAuthNonce(
                cookie_hash=_sha256(cookie),
                nonce_hash=_sha256(raw_nonce),
                provider=cast(OAuthProvider, provider),
                expires_at=expires_at,
                created_at=issued_at,
            )
        )
        return IssuedOAuthNonce(
            nonce=SecretStr(raw_nonce),
            cookie=SecretStr(cookie),
            expires_in=self.lifetime_seconds,
        )

    async def consume(
        self,
        cookie: str,
        provider: IdentityProvider,
        *,
        now: datetime | None = None,
    ) -> str:
        """Validate and atomically consume a provider-bound nonce cookie."""
        _require_oauth_provider(provider)
        consumed_at = now or datetime.now(UTC)
        try:
            payload, supplied_signature = cookie.split(".", maxsplit=1)
            expected_signature = _sign(payload, self.signing_key)
            if not hmac.compare_digest(supplied_signature, expected_signature):
                raise InvalidOAuthNonceException()
            decoded = _decode_payload(payload)
            provider_value = decoded.get("provider")
            if not isinstance(provider_value, str):
                raise InvalidOAuthNonceException()
            bound_provider = IdentityProvider(provider_value)
            _require_oauth_provider(bound_provider)
            if (
                not isinstance(decoded.get("handle"), str)
                or not isinstance(decoded.get("exp"), int)
                or decoded["exp"] <= int(consumed_at.timestamp())
            ):
                raise InvalidOAuthNonceException()
        except InvalidOAuthNonceException:
            raise
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise InvalidOAuthNonceException() from exc

        consumed = await self.repository.consume(
            cookie_hash=_sha256(cookie),
            provider=bound_provider,
            now=consumed_at,
        )
        if consumed is None or bound_provider is not provider:
            raise InvalidOAuthNonceException()
        return consumed.nonce_hash


def _require_oauth_provider(provider: IdentityProvider) -> None:
    if provider not in (IdentityProvider.GOOGLE, IdentityProvider.APPLE):
        raise InvalidOAuthNonceException()


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sign(payload: str, key: bytes) -> str:
    digest = hmac.new(key, payload.encode("ascii"), hashlib.sha256).digest()
    return _base64url_encode(digest)


def _encode_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _base64url_encode(encoded)


def _decode_payload(payload: str) -> dict[str, Any]:
    decoded = json.loads(_base64url_decode(payload))
    if not isinstance(decoded, dict):
        raise InvalidOAuthNonceException()
    return decoded


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
