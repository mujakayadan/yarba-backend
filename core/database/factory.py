"""Factory for database dependencies.

This module provides factory functions for creating database-related dependencies.
"""

from collections.abc import AsyncGenerator

from motor.motor_asyncio import AsyncIOMotorDatabase

from config.settings import Settings
from core.repositories import (
    CoverLetterRepository,
    PortfolioRepository,
    ProfileRepository,
    ResumeRepository,
    UserRepository,
)

from ..services.auth_service import AuthService
from .connection import get_async_database_connection
from .unit_of_work import AsyncMongoUnitOfWork

settings = Settings()


async def get_database() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """Get a database connection.

    Yields:
        AsyncIOMotorDatabase: MongoDB database instance
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
    yield AuthService()
