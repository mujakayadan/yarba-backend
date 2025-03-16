"""Database dependencies for FastAPI."""

from typing import Annotated

from fastapi import Depends

from core.database import (
    get_portfolio_repository,
    get_preamble_repository,
    get_profile_repository,
    get_resume_repository,
    get_tex_header_repository,
    get_unit_of_work,
    get_user_repository,
)
from core.database.unit_of_work import AsyncMongoUnitOfWork
from core.repositories.portfolio import PortfolioRepository
from core.repositories.preamble import PreambleRepository
from core.repositories.profile import ProfileRepository
from core.repositories.resume import ResumeRepository
from core.repositories.tex_header import TexHeaderRepository
from core.repositories.user import UserRepository

# Type aliases for dependency injection
UnitOfWork = Annotated[AsyncMongoUnitOfWork, Depends(get_unit_of_work)]
UserRepo = Annotated[UserRepository, Depends(get_user_repository)]
ProfileRepo = Annotated[ProfileRepository, Depends(get_profile_repository)]
PortfolioRepo = Annotated[PortfolioRepository, Depends(get_portfolio_repository)]
ResumeRepo = Annotated[ResumeRepository, Depends(get_resume_repository)]
PreambleRepo = Annotated[PreambleRepository, Depends(get_preamble_repository)]
TexHeaderRepo = Annotated[TexHeaderRepository, Depends(get_tex_header_repository)]
