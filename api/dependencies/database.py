"""Database dependencies for FastAPI."""

from typing import Annotated

from fastapi import Depends

from core.database import (
    get_portfolio_repository,
    get_preamble_repository,
    get_profile_repository,
    get_resume_repository,
    get_tex_header_repository,
    get_tex_template_repository,
    get_unit_of_work,
    get_user_repository,
)
from core.database.unit_of_work import AsyncMongoUnitOfWork
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.preamble_repository import PreambleRepository
from core.repositories.profile_repository import ProfileRepository
from core.repositories.resume_repository import ResumeRepository
from core.repositories.tex_header_repository import TexHeaderRepository
from core.repositories.tex_template_repository import TexTemplateRepository
from core.repositories.user_repository import UserRepository

# Type aliases for dependency injection
UnitOfWork = Annotated[AsyncMongoUnitOfWork, Depends(get_unit_of_work)]
UserRepo = Annotated[UserRepository, Depends(get_user_repository)]
ProfileRepo = Annotated[ProfileRepository, Depends(get_profile_repository)]
PortfolioRepo = Annotated[PortfolioRepository, Depends(get_portfolio_repository)]
ResumeRepo = Annotated[ResumeRepository, Depends(get_resume_repository)]
PreambleRepo = Annotated[PreambleRepository, Depends(get_preamble_repository)]
TexHeaderRepo = Annotated[TexHeaderRepository, Depends(get_tex_header_repository)]
TexTemplateRepo = Annotated[TexTemplateRepository, Depends(get_tex_template_repository)]
