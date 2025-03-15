"""Database module initialization.

This module provides database connection and management functionality.
"""

from .connection import (
    close_async_database_connection,
    close_database_connection,
    get_async_database_connection,
    get_database_connection,
)
from .factory import (
    get_database,
    get_portfolio_repository,
    get_preamble_repository,
    get_profile_repository,
    get_resume_repository,
    get_tex_header_repository,
    get_unit_of_work,
    get_user_repository,
)
from .init import init_db
from .unit_of_work import AsyncMongoUnitOfWork

__all__ = [
    # Connection functions
    "get_database_connection",
    "get_async_database_connection",
    "close_database_connection",
    "close_async_database_connection",
    # Factory functions
    "get_database",
    "get_user_repository",
    "get_profile_repository",
    "get_portfolio_repository",
    "get_resume_repository",
    "get_preamble_repository",
    "get_tex_header_repository",
    "get_unit_of_work",
    # Initialization
    "init_db",
    # Unit of Work
    "AsyncMongoUnitOfWork",
]
