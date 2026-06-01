"""Unit of Work pattern implementation.

This module provides a Unit of Work implementation for MongoDB.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..repositories.portfolio_repository import PortfolioRepository
from ..repositories.profile_repository import ProfileRepository
from ..repositories.resume_repository import ResumeRepository
from ..repositories.user_repository import UserRepository
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
    """

    def __init__(self, database: AsyncIOMotorDatabase | None = None):
        """Initialize the Unit of Work.

        Args:
            database: Optional MongoDB database instance
        """
        self.database = database
        self.user_repository: UserRepository | None = None
        self.resume_repository: ResumeRepository | None = None
        self.profile_repository: ProfileRepository | None = None
        self.portfolio_repository: PortfolioRepository | None = None

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

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager.

        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        # Clean up resources if needed
