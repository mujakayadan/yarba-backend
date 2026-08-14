"""Factory for database dependencies.

This module provides factory functions for creating database-related dependencies.
"""

from collections.abc import AsyncGenerator

from config.settings import settings
from core.auth.oauth import AiohttpJwksFetcher, JwksCache, OAuthIdTokenVerifier
from core.database.types import AsyncMongoDatabase
from core.repositories import (
    AgentAccessTokenRepository,
    AuthActionTokenRepository,
    AuthIdentityRepository,
    CoverLetterRepository,
    JobApplicationRepository,
    OAuthNonceRepository,
    PortfolioRepository,
    PortfolioSiteTokenRepository,
    ProfileRepository,
    RefreshTokenSessionRepository,
    ResumeRepository,
    UserRepository,
)
from core.services.email_clients.resend_client import ResendClient
from core.services.native_auth_service import NativeAuthService
from core.services.oauth_nonce_service import OAuthNonceService
from core.services.refresh_token_service import RefreshTokenService

from ..services.auth_service import AuthService
from .connection import get_async_database_connection
from .unit_of_work import AsyncMongoUnitOfWork

_oauth_jwks_cache = JwksCache(
    AiohttpJwksFetcher(),
    ttl_seconds=settings.auth.oauth_jwks_cache_ttl_seconds,
)
_oauth_id_token_verifier = OAuthIdTokenVerifier(
    cache=_oauth_jwks_cache,
    google_jwks_url=settings.auth.oauth_google_jwks_url,
    apple_jwks_url=settings.auth.oauth_apple_jwks_url,
    google_issuers=settings.auth.google_oauth_issuer_allowlist,
    apple_issuer=settings.auth.oauth_apple_issuer,
    google_audiences=settings.auth.google_oauth_audience_allowlist,
    apple_audiences=settings.auth.apple_oauth_audience_allowlist,
)


def _build_resend_client() -> ResendClient | None:
    """Return a Resend client when outbound email is configured."""
    api_key = settings.resend.api_key.get_secret_value()
    if not api_key:
        return None
    return ResendClient(api_key=api_key, from_address=settings.resend.from_address)


async def get_database() -> AsyncGenerator[AsyncMongoDatabase, None]:
    """Get a database connection.

    Yields:
        AsyncMongoDatabase: MongoDB database instance
    """
    db = await get_async_database_connection()
    try:
        yield db
    finally:
        # Connection is managed globally, no need to close here
        pass


async def get_user_repository() -> AsyncGenerator[UserRepository, None]:
    """Get a user repository.

    Yields:
        UserRepository: User repository instance
    """
    yield UserRepository()


async def get_profile_repository() -> AsyncGenerator[ProfileRepository, None]:
    """Get a profile repository.

    Yields:
        ProfileRepository: Profile repository instance
    """
    yield ProfileRepository()


async def get_portfolio_repository() -> AsyncGenerator[PortfolioRepository, None]:
    """Get a portfolio repository.

    Yields:
        PortfolioRepository: Portfolio repository instance
    """
    yield PortfolioRepository()


async def get_portfolio_site_token_repository() -> AsyncGenerator[
    PortfolioSiteTokenRepository, None
]:
    """Get a portfolio site token repository."""
    yield PortfolioSiteTokenRepository()


async def get_agent_access_token_repository() -> AsyncGenerator[
    AgentAccessTokenRepository, None
]:
    """Get an agent access token repository."""
    yield AgentAccessTokenRepository()


async def get_job_application_repository() -> AsyncGenerator[
    JobApplicationRepository, None
]:
    """Get a job application repository."""
    yield JobApplicationRepository()


async def get_resume_repository() -> AsyncGenerator[ResumeRepository, None]:
    """Get a resume repository.

    Yields:
        ResumeRepository: Resume repository instance
    """
    yield ResumeRepository()


async def get_cover_letter_repository() -> AsyncGenerator[CoverLetterRepository, None]:
    """Get a cover letter repository.

    Yields:
        CoverLetterRepository: Cover letter repository instance
    """
    yield CoverLetterRepository()


async def get_unit_of_work() -> AsyncGenerator[AsyncMongoUnitOfWork, None]:
    """Get a Unit of Work.

    Yields:
        AsyncMongoUnitOfWork: Unit of Work instance
    """
    async with AsyncMongoUnitOfWork() as uow:
        yield uow


async def get_auth_service() -> AsyncGenerator[AuthService, None]:
    """Get authentication service instance.

    This service handles all authentication operations using Firebase.

    Yields:
        AuthService: Authentication service instance
    """
    yield AuthService(resend_client=_build_resend_client())


async def get_native_auth_service() -> AsyncGenerator[NativeAuthService, None]:
    """Yield the composed backend-owned authentication service."""
    resend_client = _build_resend_client()
    auth_service = AuthService(resend_client=resend_client)
    yield NativeAuthService(
        user_repository=UserRepository(),
        identity_repository=AuthIdentityRepository(),
        action_token_repository=AuthActionTokenRepository(),
        refresh_token_service=RefreshTokenService(RefreshTokenSessionRepository()),
        auth_service=auth_service,
        resend_client=resend_client,
    )


def get_oauth_id_token_verifier() -> OAuthIdTokenVerifier:
    """Return the process-wide verifier and bounded JWKS cache."""
    return _oauth_id_token_verifier


def get_oauth_nonce_service() -> OAuthNonceService:
    """Return the backend-issued OAuth nonce service."""
    return OAuthNonceService(
        OAuthNonceRepository(),
        signing_key=settings.auth.jwt_secret_key.get_secret_value(),
        lifetime_seconds=settings.auth.oauth_nonce_cookie_max_age_seconds,
    )
