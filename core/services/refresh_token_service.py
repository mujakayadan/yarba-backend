"""Refresh-token issuance, rotation, revocation, and reuse handling."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from beanie import PydanticObjectId
from pydantic import SecretStr

from config.settings import settings
from core.models.refresh_token_session import (
    RefreshTokenDeviceMetadata,
    RefreshTokenSession,
)
from core.repositories.refresh_token_session_repository import (
    RefreshTokenSessionRepository,
)
from core.utils.refresh_token import generate_refresh_token, hash_refresh_token


class RefreshTokenError(Exception):
    """Base error for refresh-token state transitions."""


class InvalidRefreshTokenError(RefreshTokenError):
    """Raised when no refresh-token session recognizes the token."""


class ExpiredRefreshTokenError(RefreshTokenError):
    """Raised when a current refresh token has expired."""


class RevokedRefreshTokenError(RefreshTokenError):
    """Raised when a current refresh-token family has been revoked."""


class RefreshTokenReuseError(RefreshTokenError):
    """Raised after a reused rotated token revokes its entire family."""


@dataclass(frozen=True, slots=True)
class IssuedRefreshToken:
    """Raw token returned once alongside its persisted session."""

    token: SecretStr
    session: RefreshTokenSession


class RefreshTokenService:
    """Manage opaque refresh tokens without persisting plaintext values."""

    def __init__(
        self,
        repository: RefreshTokenSessionRepository | None = None,
        *,
        token_lifetime: timedelta | None = None,
    ) -> None:
        self.repository = repository or RefreshTokenSessionRepository()
        self.token_lifetime = token_lifetime or timedelta(
            days=settings.auth.jwt_refresh_token_expire_days
        )

    async def create_session(
        self,
        *,
        user_id: PydanticObjectId,
        device: RefreshTokenDeviceMetadata | None = None,
        now: datetime | None = None,
    ) -> IssuedRefreshToken:
        """Create a new token family and return its raw token once."""
        issued_at = now or datetime.now(UTC)
        raw_token = generate_refresh_token()
        session = RefreshTokenSession(
            user_id=user_id,
            family_id=str(uuid4()),
            token_hash=hash_refresh_token(raw_token),
            expires_at=issued_at + self.token_lifetime,
            device=device,
            created_at=issued_at,
            updated_at=issued_at,
        )
        await self.repository.create(session)
        return IssuedRefreshToken(token=SecretStr(raw_token), session=session)

    async def rotate(
        self,
        raw_token: str,
        *,
        now: datetime | None = None,
    ) -> IssuedRefreshToken:
        """Rotate a current token or revoke its family when reuse is detected."""
        rotated_at = now or datetime.now(UTC)
        current_hash = hash_refresh_token(raw_token)
        replacement = generate_refresh_token()
        replacement_hash = hash_refresh_token(replacement)

        session = await self.repository.rotate_current_hash(
            current_hash=current_hash,
            replacement_hash=replacement_hash,
            now=rotated_at,
        )
        if session is not None:
            return IssuedRefreshToken(token=SecretStr(replacement), session=session)

        reused_session = await self.repository.revoke_reused_family(
            reused_hash=current_hash,
            now=rotated_at,
        )
        if reused_session is not None:
            raise RefreshTokenReuseError(
                "Refresh token reuse detected; the token family was revoked"
            )

        current_session = await self.repository.get_by_token_hash(current_hash)
        if current_session is None:
            raise InvalidRefreshTokenError("Refresh token is not recognized")
        if current_session.revoked_at is not None:
            raise RevokedRefreshTokenError("Refresh token family is revoked")
        if _as_utc(current_session.expires_at) <= _as_utc(rotated_at):
            raise ExpiredRefreshTokenError("Refresh token has expired")
        raise InvalidRefreshTokenError("Refresh token could not be rotated")

    async def revoke_family(
        self,
        *,
        family_id: str,
        reason: str = "user_revoked",
        now: datetime | None = None,
    ) -> RefreshTokenSession | None:
        """Revoke one refresh-token family."""
        return await self.repository.revoke_family(
            family_id=family_id,
            reason=reason,
            now=now or datetime.now(UTC),
        )

    async def revoke_token(
        self,
        raw_token: str,
        *,
        reason: str,
        now: datetime | None = None,
    ) -> RefreshTokenSession | None:
        """Revoke the family identified by a current raw token."""
        session = await self.repository.get_by_token_hash(hash_refresh_token(raw_token))
        if session is None:
            return None
        return await self.revoke_family(
            family_id=session.family_id,
            reason=reason,
            now=now,
        )

    async def revoke_all_for_user(
        self,
        *,
        user_id: PydanticObjectId,
        reason: str = "user_revoked_all",
        now: datetime | None = None,
    ) -> int:
        """Revoke every active refresh-token family for a user."""
        return await self.repository.revoke_all_for_user(
            user_id=user_id,
            reason=reason,
            now=now or datetime.now(UTC),
        )


def _as_utc(value: datetime) -> datetime:
    """Normalize MongoDB's potentially naive UTC datetimes for comparison."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
