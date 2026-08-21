"""Database initialization module.

This module provides functions for initializing the database connection
and setting up the database for the application.
"""

from pathlib import Path

# Load environment variables from .env files
try:
    from dotenv import load_dotenv

    # Load environment variables from .env.local first, then fallback to others
    for env_file in [".env.local", ".env.production", ".env"]:
        if Path(env_file).exists():
            load_dotenv(dotenv_path=env_file)
            break
except ImportError:
    # dotenv is optional, so handle the case where it's not installed
    pass

from beanie import init_beanie
from pymongo import AsyncMongoClient

from config.logging_config import get_logger
from config.settings import Settings
from core.database.types import AsyncMongoClientType
from core.models.agent_access_token import AgentAccessToken
from core.models.auth_action_token import AuthActionToken
from core.models.auth_identity import AuthIdentity
from core.models.cover_letter import CoverLetter
from core.models.data_rights import AccountDeletionRequest, AccountExportRequest
from core.models.inbound_email import InboundEmail
from core.models.job_application import JobApplication
from core.models.legal import LegalAcceptance, LegalDocumentVersion
from core.models.oauth_nonce import OAuthNonce
from core.models.portfolio import Portfolio
from core.models.portfolio_chat_conversation import PortfolioChatConversation
from core.models.portfolio_site_token import PortfolioSiteToken
from core.models.portfolio_website import PortfolioWebsite
from core.models.profile import Profile
from core.models.refresh_token_session import RefreshTokenSession
from core.models.resume import Resume
from core.models.safety import AbuseReport, ModerationAuditEvent
from core.models.unknown_email_sender import UnknownEmailSender
from core.models.user import User
from utils.text import sanitize_mongodb_uri

logger = get_logger(__name__)
settings = Settings()


async def init_db() -> AsyncMongoClientType | None:
    """Initialize database connection.

    Returns:
        Optional[AsyncMongoClient]: Database client if successful, None otherwise.
    """
    try:
        mongodb_uri = settings.database.url
        mongodb_db = settings.database.name

        sanitized_uri = sanitize_mongodb_uri(mongodb_uri)
        logger.info(
            f"Connecting to MongoDB at: {sanitized_uri} (database: {mongodb_db})"
        )

        if mongodb_uri.startswith("mongodb://localhost"):
            logger.warning(
                "Using a local MongoDB URI. If you intended to connect to a remote database, "
                "make sure the MONGODB_URI environment variable is set in .env.local file."
            )

        client: AsyncMongoClientType = AsyncMongoClient(
            mongodb_uri,
            minPoolSize=settings.database.min_pool_size,
            maxPoolSize=settings.database.max_pool_size,
            serverSelectionTimeoutMS=settings.database.server_selection_timeout_ms,
            connectTimeoutMS=settings.database.connection_timeout_ms,
            socketTimeoutMS=settings.database.socket_timeout_ms,
            retryWrites=settings.database.retry_writes,
            retryReads=settings.database.retry_reads,
        )

        document_models = [
            User,
            AuthActionToken,
            AuthIdentity,
            OAuthNonce,
            RefreshTokenSession,
            Resume,
            CoverLetter,
            Profile,
            Portfolio,
            PortfolioSiteToken,
            AgentAccessToken,
            JobApplication,
            PortfolioWebsite,
            PortfolioChatConversation,
            InboundEmail,
            UnknownEmailSender,
            LegalDocumentVersion,
            LegalAcceptance,
            AbuseReport,
            ModerationAuditEvent,
            AccountExportRequest,
            AccountDeletionRequest,
        ]

        logger.info("Testing MongoDB connection...")
        await client.admin.command("ping")
        logger.info("MongoDB connection test successful")

        logger.info(f"Initializing Beanie with database: {mongodb_db}")
        await init_beanie(
            database=client[mongodb_db],
            document_models=document_models,
        )

        logger.info("Successfully initialized database connection and Beanie ODM")
        return client

    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        import traceback

        logger.error(f"Error details: {traceback.format_exc()}")
        return None
