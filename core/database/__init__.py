"""Database module initialization.

This module provides database connection and management functionality.
"""

# Import repository factories
from ..repositories.portfolio import get_portfolio_repository
from ..repositories.preamble import get_preamble_repository
from ..repositories.profile import get_profile_repository
from ..repositories.resume import get_resume_repository
from ..repositories.tex_header import get_tex_header_repository
from ..repositories.tex_template import get_tex_template_repository
from ..repositories.user import get_user_repository
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
    get_tex_template_repository,
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
    "get_tex_header_repository",
    "get_tex_template_repository",
    "get_preamble_repository",
    "get_unit_of_work",
    # Initialization
    "init_db",
    # Unit of Work
    "AsyncMongoUnitOfWork",
]
