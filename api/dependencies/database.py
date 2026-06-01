"""Database dependencies for FastAPI."""

from typing import Annotated

from fastapi import Depends

# Import factory functions from core.database.factory
from core.database.factory import (
    get_portfolio_repository,
    get_profile_repository,
    get_resume_repository,
    get_unit_of_work,
    get_user_repository,
)
from core.database.unit_of_work import AsyncMongoUnitOfWork
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.profile_repository import ProfileRepository
from core.repositories.resume_repository import ResumeRepository
from core.repositories.user_repository import UserRepository

# Type aliases for dependency injection
UnitOfWork = Annotated[AsyncMongoUnitOfWork, Depends(get_unit_of_work)]
UserRepo = Annotated[UserRepository, Depends(get_user_repository)]
ProfileRepo = Annotated[ProfileRepository, Depends(get_profile_repository)]
PortfolioRepo = Annotated[PortfolioRepository, Depends(get_portfolio_repository)]
ResumeRepo = Annotated[ResumeRepository, Depends(get_resume_repository)]
