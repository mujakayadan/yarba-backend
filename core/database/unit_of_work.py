"""Unit of Work pattern implementation.

This module provides a Unit of Work implementation for MongoDB.
"""

from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..repositories.preamble import PreambleRepository
from ..repositories.tex_header import TexHeaderRepository
from ..repositories.portfolio import PortfolioRepository
from ..repositories.profile import ProfileRepository
from ..repositories.resume import ResumeRepository
from ..repositories.user import UserRepository
from .connection import get_async_database_connection


class AsyncMongoUnitOfWork:
    """Asynchronous Unit of Work for MongoDB.

    This class provides a Unit of Work implementation for MongoDB
    using the repository pattern. It manages the database connection
    and repositories for different entities.

    Attributes:
        database: The MongoDB database instance
        user_repository: Repository for user data
        resume_repository: Repository for resume data
        profile_repository: Repository for profile data
        portfolio_repository: Repository for portfolio data
        tex_header_repository: Repository for TeX headers
        preamble_repository: Repository for preambles
    """

    def __init__(self, database: Optional[AsyncIOMotorDatabase] = None):
        """Initialize the Unit of Work.

        Args:
            database: Optional MongoDB database instance
        """
        self.database = database
        self.user_repository: Optional[UserRepository] = None
        self.resume_repository: Optional[ResumeRepository] = None
        self.profile_repository: Optional[ProfileRepository] = None
        self.portfolio_repository: Optional[PortfolioRepository] = None
        self.tex_header_repository: Optional[TexHeaderRepository] = None
        self.preamble_repository: Optional[PreambleRepository] = None

    async def __aenter__(self):
        """Enter the context manager.

        Returns:
            AsyncMongoUnitOfWork: The Unit of Work instance
        """
        # Get database connection if not provided
        if self.database is None:
            self.database = await get_async_database_connection()

        # Initialize repositories
        self.user_repository = UserRepository()
        self.resume_repository = ResumeRepository()
        self.profile_repository = ProfileRepository()
        self.portfolio_repository = PortfolioRepository()
        self.tex_header_repository = TexHeaderRepository()
        self.preamble_repository = PreambleRepository()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager.

        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        # Clean up resources if needed
        pass
