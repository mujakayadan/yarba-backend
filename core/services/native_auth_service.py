"""Backend-owned password authentication and account action lifecycle."""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from beanie import PydanticObjectId
from pydantic import EmailStr, SecretStr
from pymongo.errors import DuplicateKeyError

from api.schemas.legal import LegalAcceptanceRequest
from config.settings import settings
from core.auth.oauth import VerifiedProviderIdentity
from core.auth.password import get_password_hash, verify_password
from core.auth.types import AuthMigrationState, IdentityProvider
from core.exceptions.base import (
    BadRequestException,
    ConflictException,
    UnauthorizedException,
)
from core.models.auth_action_token import AuthActionPurpose, AuthActionToken
from core.models.auth_identity import AuthIdentity
from core.models.user import User
from core.repositories.auth_action_token_repository import AuthActionTokenRepository
from core.repositories.auth_identity_repository import AuthIdentityRepository
from core.repositories.user_repository import UserRepository
from core.services.auth_service import AuthService
from core.services.email_clients.resend_client import ResendClient
from core.services.legal_service import LegalService
from core.services.refresh_token_service import IssuedRefreshToken, RefreshTokenService
from core.utils.auth_action_token import (
    generate_auth_action_token,
    hash_auth_action_token,
)
from core.utils.object_id import require_object_id

_DUMMY_PASSWORD_HASH = get_password_hash("YarbaDummyPassword123")


@dataclass(frozen=True, slots=True)
class NativeAuthResult:
    """Access token, refresh session, and user returned after authentication."""

    user: User
    access_token: str
    access_token_expires_in: int
    refresh: IssuedRefreshToken


class NativeAuthService:
    """Implement native password, session, reset, and verification flows."""

    def __init__(
        self,
        *,
        user_repository: UserRepository | None = None,
        identity_repository: AuthIdentityRepository | None = None,
        action_token_repository: AuthActionTokenRepository | None = None,
        refresh_token_service: RefreshTokenService | None = None,
        auth_service: AuthService | None = None,
        resend_client: ResendClient | None = None,
        legal_service: LegalService | None = None,
    ) -> None:
        self.users = user_repository or UserRepository()
        self.identities = identity_repository or AuthIdentityRepository()
        self.action_tokens = action_token_repository or AuthActionTokenRepository()
        self.refresh_tokens = refresh_token_service or RefreshTokenService()
        self.auth_service = auth_service or AuthService()
        self.resend_client = resend_client
        self.legal = legal_service or LegalService()

    async def register(
        self,
        email: EmailStr,
        password: str,
        legal_acceptance: LegalAcceptanceRequest | None = None,
    ) -> NativeAuthResult:
        """Create a native-only user without claiming an existing email."""
        if legal_acceptance is not None:
            await self.legal.validate(legal_acceptance)
        canonical_email = _canonicalize_email(email)
        if await self.users.get_by_email_insensitive(canonical_email) is not None:
            raise ConflictException("Registration is unavailable for these credentials")

        username = await self._unique_username(
            canonical_email.split("@", maxsplit=1)[0]
        )
        try:
            user = await self.users.create(
                User(
                    username=username,
                    email=canonical_email,
                    firebase_uid=None,
                    auth_provider="password",
                    password_hash=get_password_hash(password),
                    auth_migration_state=AuthMigrationState.NATIVE,
                    email_verified=False,
                )
            )
        except DuplicateKeyError as exc:
            raise ConflictException(
                "Registration is unavailable for these credentials"
            ) from exc
        user_id = require_object_id(user.id)
        await self.identities.create(
            AuthIdentity(
                user_id=user_id,
                provider=IdentityProvider.PASSWORD,
                provider_subject=str(user_id),
                provider_email=_canonicalize_email(user.email),
            )
        )
        if legal_acceptance is not None:
            await self.legal.accept(user_id, legal_acceptance)
        await self._send_verification_if_configured(user)
        return await self._issue_auth_result(user)

    async def login(self, email: EmailStr, password: str) -> NativeAuthResult:
        """Authenticate without revealing whether an account or password exists."""
        user = await self.users.get_by_email_insensitive(_canonicalize_email(email))
        password_hash = user.password_hash if user and user.password_hash else None
        password_valid = verify_password(
            password,
            password_hash or _DUMMY_PASSWORD_HASH,
        )
        if (
            user is None
            or password_hash is None
            or not password_valid
            or not user.is_active
        ):
            raise UnauthorizedException("Invalid email or password")

        await self.users.update_last_login(require_object_id(user.id))
        refreshed_user = await self.users.get_by_id(require_object_id(user.id))
        return await self._issue_auth_result(refreshed_user or user)

    async def oauth_login(
        self,
        verified: VerifiedProviderIdentity,
        legal_acceptance: LegalAcceptanceRequest | None = None,
    ) -> NativeAuthResult:
        """Resolve or create a provider identity without linking by email."""
        identity = await self.identities.get_by_provider_subject(
            verified.provider,
            verified.subject,
        )
        if identity is not None:
            user = await self.users.get_by_id(identity.user_id)
            if user is None or not user.is_active:
                raise UnauthorizedException("Invalid provider identity")
            await self.users.update_last_login(require_object_id(user.id))
            refreshed = await self.users.get_by_id(require_object_id(user.id))
            return await self._issue_auth_result(refreshed or user)

        if verified.email is None:
            raise BadRequestException(
                "Provider profile is incomplete; retry sign-in with email sharing",
                error_code="provider_profile_incomplete",
            )
        if legal_acceptance is None:
            raise BadRequestException(
                "Legal acceptance is required for first-time provider sign-in",
                error_code="legal_acceptance_required",
            )
        await self.legal.validate(legal_acceptance)
        canonical_email = _canonicalize_email(verified.email)
        if await self.users.get_by_email_insensitive(canonical_email) is not None:
            raise ConflictException(
                "Account linking is required",
                error_code="account_linking_required",
            )

        username_source = verified.display_name or canonical_email.split("@", 1)[0]
        username = await self._unique_username(username_source)
        try:
            user = await self.users.create(
                User(
                    username=username,
                    email=canonical_email,
                    firebase_uid=None,
                    auth_provider=verified.provider.value,
                    auth_migration_state=AuthMigrationState.NATIVE,
                    email_verified=True,
                )
            )
        except DuplicateKeyError as exc:
            winner = await self._reload_provider_user(verified)
            if winner is not None:
                return await self._issue_auth_result(winner)
            raise ConflictException(
                "Account linking is required",
                error_code="account_linking_required",
            ) from exc

        user_id = require_object_id(user.id)
        try:
            await self.identities.create(
                AuthIdentity(
                    user_id=user_id,
                    provider=verified.provider,
                    provider_subject=verified.subject,
                    provider_email=canonical_email,
                )
            )
        except DuplicateKeyError:
            await self.users.delete(user_id)
            winner = await self._reload_provider_user(verified)
            if winner is None:
                raise ConflictException("Provider sign-in could not be completed")
            return await self._issue_auth_result(winner)
        except Exception:
            await self.users.delete(user_id)
            raise
        await self.legal.accept(user_id, legal_acceptance)
        return await self._issue_auth_result(user)

    async def refresh(self, raw_token: str) -> NativeAuthResult:
        """Rotate a refresh token and issue a new short-lived access token."""
        rotated = await self.refresh_tokens.rotate(raw_token)
        user = await self.users.get_by_id(rotated.session.user_id)
        if user is None or not user.is_active:
            await self.refresh_tokens.revoke_family(
                family_id=rotated.session.family_id,
                reason="user_inactive",
            )
            raise UnauthorizedException("Invalid session")
        return self._build_auth_result(user, rotated)

    async def logout(self, raw_token: str) -> None:
        """Revoke the current refresh-token family when it is recognized."""
        await self.refresh_tokens.revoke_token(raw_token, reason="logout")

    async def logout_all(self, user_id: PydanticObjectId) -> int:
        """Revoke all refresh-token families for a user."""
        return await self.refresh_tokens.revoke_all_for_user(
            user_id=user_id,
            reason="logout_all",
        )

    async def request_password_reset(self, email: EmailStr) -> None:
        """Send a reset link when eligible while remaining enumeration-safe."""
        user = await self.users.get_by_email_insensitive(_canonicalize_email(email))
        if user is None or not user.is_active or self.resend_client is None:
            return
        raw = await self.issue_action_token(
            user_id=require_object_id(user.id),
            purpose=AuthActionPurpose.PASSWORD_RESET,
            lifetime=timedelta(
                minutes=settings.auth.password_reset_token_expire_minutes
            ),
        )
        await self._send_action_email(
            user=user,
            raw_token=raw,
            path=settings.auth.password_reset_path,
            subject="Reset your YARBA password",
            action_label="Reset password",
        )

    async def reset_password(self, raw_token: str, new_password: str) -> User:
        """Consume a reset token and set or replace the native password."""
        token = await self._consume_action_token(
            raw_token,
            AuthActionPurpose.PASSWORD_RESET,
        )
        user = await self._require_action_user(token)
        await self._set_native_password(user, new_password)
        await self.refresh_tokens.revoke_all_for_user(
            user_id=require_object_id(user.id),
            reason="password_reset",
        )
        return user

    async def request_verification(self, email: EmailStr) -> None:
        """Send a verification link without revealing account state."""
        user = await self.users.get_by_email_insensitive(_canonicalize_email(email))
        if (
            user is None
            or not user.is_active
            or user.email_verified
            or self.resend_client is None
        ):
            return
        raw = await self.issue_action_token(
            user_id=require_object_id(user.id),
            purpose=AuthActionPurpose.EMAIL_VERIFICATION,
            lifetime=timedelta(
                minutes=settings.auth.email_verification_token_expire_minutes
            ),
        )
        await self._send_action_email(
            user=user,
            raw_token=raw,
            path=settings.auth.email_verification_path,
            subject="Verify your YARBA email",
            action_label="Verify email",
        )

    async def confirm_verification(self, raw_token: str) -> User:
        """Consume a verification token and mark the email verified."""
        token = await self._consume_action_token(
            raw_token,
            AuthActionPurpose.EMAIL_VERIFICATION,
        )
        user = await self._require_action_user(token)
        user.email_verified = True
        user.updated_at = datetime.now(UTC)
        await user.save()
        return user

    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
    ) -> None:
        """Change an existing native password and revoke refresh sessions."""
        if not user.password_hash or not verify_password(
            current_password,
            user.password_hash,
        ):
            raise UnauthorizedException("Invalid current password")
        await self._set_native_password(user, new_password)
        await self.refresh_tokens.revoke_all_for_user(
            user_id=require_object_id(user.id),
            reason="password_changed",
        )

    async def deactivate(self, user: User) -> User:
        """Use the established soft-deactivation behavior and revoke sessions."""
        user_id = require_object_id(user.id)
        deactivated = await self.auth_service.deactivate_user(user_id)
        await self.refresh_tokens.revoke_all_for_user(
            user_id=user_id,
            reason="account_deactivated",
        )
        return deactivated

    async def issue_action_token(
        self,
        *,
        user_id: PydanticObjectId,
        purpose: AuthActionPurpose,
        lifetime: timedelta,
        now: datetime | None = None,
    ) -> SecretStr:
        """Create a one-time opaque token, returning plaintext only to the caller."""
        issued_at = now or datetime.now(UTC)
        await self.action_tokens.supersede_active(
            user_id=user_id,
            purpose=purpose,
            now=issued_at,
        )
        raw_token = generate_auth_action_token()
        await self.action_tokens.create(
            AuthActionToken(
                token_hash=hash_auth_action_token(raw_token),
                purpose=purpose,
                user_id=user_id,
                expires_at=issued_at + lifetime,
                created_at=issued_at,
            )
        )
        return SecretStr(raw_token)

    async def _issue_auth_result(self, user: User) -> NativeAuthResult:
        refresh = await self.refresh_tokens.create_session(
            user_id=require_object_id(user.id)
        )
        return self._build_auth_result(user, refresh)

    def _build_auth_result(
        self,
        user: User,
        refresh: IssuedRefreshToken,
    ) -> NativeAuthResult:
        lifetime_minutes = settings.auth.jwt_native_access_token_expire_minutes
        access_token = self.auth_service.create_access_token(
            data={"sub": str(user.email)},
            expires_delta=timedelta(minutes=lifetime_minutes),
        )
        return NativeAuthResult(
            user=user,
            access_token=access_token,
            access_token_expires_in=lifetime_minutes * 60,
            refresh=refresh,
        )

    async def _consume_action_token(
        self,
        raw_token: str,
        purpose: AuthActionPurpose,
    ) -> AuthActionToken:
        token = await self.action_tokens.consume(
            token_hash=hash_auth_action_token(raw_token),
            purpose=purpose,
            now=datetime.now(UTC),
        )
        if token is None:
            raise BadRequestException("Invalid or expired action token")
        return token

    async def _require_action_user(self, token: AuthActionToken) -> User:
        user = await self.users.get_by_id(token.user_id)
        if user is None or not user.is_active:
            raise BadRequestException("Invalid or expired action token")
        return user

    async def _set_native_password(self, user: User, password: str) -> None:
        user.password_hash = get_password_hash(password)
        user.auth_migration_state = (
            AuthMigrationState.DUAL
            if user.firebase_uid is not None
            else AuthMigrationState.NATIVE
        )
        user.updated_at = datetime.now(UTC)
        await user.save()
        await self._ensure_password_identity(user)

    async def _ensure_password_identity(self, user: User) -> None:
        user_id = require_object_id(user.id)
        subject = str(user_id)
        identity = await self.identities.get_by_provider_subject(
            IdentityProvider.PASSWORD,
            subject,
        )
        if identity is None:
            await self.identities.create(
                AuthIdentity(
                    user_id=user_id,
                    provider=IdentityProvider.PASSWORD,
                    provider_subject=subject,
                    provider_email=_canonicalize_email(user.email),
                )
            )

    async def _reload_provider_user(
        self,
        verified: VerifiedProviderIdentity,
    ) -> User | None:
        """Reload a concurrent winner after a provider/email unique-index race."""
        for _ in range(4):
            identity = await self.identities.get_by_provider_subject(
                verified.provider,
                verified.subject,
            )
            if identity is not None:
                return await self.users.get_by_id(identity.user_id)
            await asyncio.sleep(0.01)
        return None

    async def _unique_username(self, base: str) -> str:
        normalized = base.lower().replace(" ", "_")
        if await self.users.get_by_username(normalized) is None:
            return normalized
        suffix = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
        return f"{normalized}_{suffix}"

    async def _send_verification_if_configured(self, user: User) -> None:
        if self.resend_client is None:
            return
        try:
            await self.request_verification(user.email)
        except Exception:
            # Registration remains usable if transactional email is temporarily down.
            return

    async def _send_action_email(
        self,
        *,
        user: User,
        raw_token: SecretStr,
        path: str,
        subject: str,
        action_label: str,
    ) -> None:
        if self.resend_client is None:
            return
        query = urlencode({"token": raw_token.get_secret_value()})
        link = f"{settings.frontend_url.rstrip('/')}{path}?{query}"
        text = f"{action_label}: {link}\n\nIf you did not request this, ignore it."
        html = (
            f'<p><a href="{link}">{action_label}</a></p>'
            "<p>If you did not request this, ignore it.</p>"
        )
        await self.resend_client.send_email(
            to=str(user.email),
            subject=subject,
            text=text,
            html=html,
        )


def _canonicalize_email(email: str) -> str:
    """Return the canonical value used for native persistence and snapshots."""
    return str(email).strip().lower()
