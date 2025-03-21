"""Factory for database dependencies.

This module provides factory functions for creating database-related dependencies.
"""

from typing import AsyncGenerator

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..repositories.portfolio import PortfolioRepository
from ..repositories.preamble import PreambleRepository
from ..repositories.profile import ProfileRepository
from ..repositories.resume import ResumeRepository
from ..repositories.tex_header import TexHeaderRepository
from ..repositories.tex_template import TexTemplateRepository
from ..repositories.user import UserRepository
from .connection import get_async_database_connection
from .unit_of_work import AsyncMongoUnitOfWork


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


async def get_preamble_repository() -> AsyncGenerator[PreambleRepository, None]:
    """Get a preamble repository.

    Yields:
        PreambleRepository: Preamble repository instance
    """
    yield PreambleRepository()


async def get_tex_header_repository() -> AsyncGenerator[TexHeaderRepository, None]:
    """Get a TeX header repository.

    Yields:
        TexHeaderRepository: TeX header repository instance
    """
    yield TexHeaderRepository()


async def get_tex_template_repository() -> AsyncGenerator[TexTemplateRepository, None]:
    """Get a TeX template repository.

    Yields:
        TexTemplateRepository: TeX template repository instance
    """
    yield TexTemplateRepository()


async def get_unit_of_work() -> AsyncGenerator[AsyncMongoUnitOfWork, None]:
    """Get a Unit of Work.

    Yields:
        AsyncMongoUnitOfWork: Unit of Work instance
    """
    async with AsyncMongoUnitOfWork() as uow:
        yield uow
