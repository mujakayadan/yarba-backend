"""Service dependencies for the API.

This module provides FastAPI dependencies for service layers.
"""

from fastapi import Depends

from core.database.factory import (
    get_cover_letter_repository,
    get_portfolio_repository,
    get_profile_repository,
    get_resume_repository,
    get_user_repository,
)
from core.repositories.cover_letter_repository import CoverLetterRepository
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.profile_repository import ProfileRepository
from core.repositories.resume_repository import ResumeRepository
from core.repositories.user_repository import UserRepository
from core.services.cover_letter_generation_service import CoverLetterGenerationService
from core.services.cover_letter_service import CoverLetterService
from core.services.job_service import JobService
from core.services.latex_service import LatexService, get_latex_service
from core.services.llm_service import LLMService
from core.services.portfolio_service import PortfolioService
from core.services.profile_service import ProfileService
from core.services.prompt_service import PromptService
from core.services.resume_generation_service import ResumeGenerationService
from core.services.resume_service import ResumeService


async def get_latex_service() -> LatexService:
    """Get a LaTeX service.

    Args: None

    Returns:
        LatexService: LaTeX service
    """
    return LatexService()


async def get_prompt_service() -> PromptService:
    """Get a prompt service.

    Returns:
        PromptService: Prompt service
    """
    return PromptService()


async def get_llm_service(
    profile_repo=Depends(get_profile_repository),
    prompt_service: PromptService = Depends(get_prompt_service),
) -> LLMService:
    """Get a LLM service.

    Args:
        profile_repo: Profile repository
        prompt_service: Prompt service

    Returns:
        LLMService: LLM service
    """
    return LLMService(
        profile_repository=profile_repo,
        prompt_service=prompt_service,
    )


async def get_job_service(
    llm_service: LLMService = Depends(get_llm_service),
    prompt_service: PromptService = Depends(get_prompt_service),
) -> JobService:
    """Get a job service.

    Args:
        llm_service: LLM service
        prompt_service: Prompt service

    Returns:
        JobService: Job service
    """
    return JobService(
        llm_service=llm_service,
        prompt_service=prompt_service,
    )


async def get_resume_service(
    user_repo=Depends(get_user_repository),
    resume_repo=Depends(get_resume_repository),
    job_service=Depends(get_job_service),
) -> ResumeService:
    """Get a resume service.

    Returns:
        ResumeService: Resume service
    """
    return ResumeService(
        user_repository=user_repo,
        resume_repository=resume_repo,
        job_service=job_service,
    )


async def get_profile_service(
    profile_repo=Depends(get_profile_repository),
    user_repo=Depends(get_user_repository),
) -> ProfileService:
    """Get a profile service.

    Args:
        profile_repo: Profile repository
        user_repo: User repository

    Returns:
        ProfileService: Profile service instance
    """
    return ProfileService(profile_repo, user_repo)


def get_portfolio_service(
    portfolio_repo=Depends(get_portfolio_repository),
    user_repo=Depends(get_user_repository),
) -> PortfolioService:
    """Get a portfolio service.

    Returns:
        PortfolioService: Portfolio service
    """
    return PortfolioService(
        portfolio_repository=portfolio_repo,
        user_repository=user_repo,
    )


def get_cover_letter_service(
    user_repo=Depends(get_user_repository),
    cover_letter_repo=Depends(get_cover_letter_repository),
    profile_repo=Depends(get_profile_repository),
    portfolio_repo=Depends(get_portfolio_repository),
    resume_repo=Depends(get_resume_repository),
    job_service=Depends(get_job_service),
) -> CoverLetterService:
    """Get a cover letter service.

    Returns:
        CoverLetterService: Cover letter service
    """
    return CoverLetterService(
        user_repository=user_repo,
        cover_letter_repository=cover_letter_repo,
        profile_repository=profile_repo,
        portfolio_repository=portfolio_repo,
        resume_repository=resume_repo,
        job_service=job_service,
    )


def get_resume_generation_service(
    resume_repo=Depends(get_resume_repository),
    portfolio_repo=Depends(get_portfolio_repository),
    profile_repo=Depends(get_profile_repository),
    llm_service=Depends(get_llm_service),
    latex_service=Depends(get_latex_service),
) -> ResumeGenerationService:
    """Get a resume generation service.

    Returns:
        ResumeGenerationService: Resume generation service
    """
    prompt_service = PromptService(user_repository=profile_repo)
    return ResumeGenerationService(
        resume_repository=resume_repo,
        portfolio_repository=portfolio_repo,
        profile_repository=profile_repo,
        llm_service=llm_service,
        prompt_service=prompt_service,
        latex_service=latex_service,
    )


def get_cover_letter_generation_service(
    cover_letter_repo=Depends(get_cover_letter_repository),
    portfolio_repo=Depends(get_portfolio_repository),
    profile_repo=Depends(get_profile_repository),
    resume_repo=Depends(get_resume_repository),
    llm_service=Depends(get_llm_service),
    latex_service=Depends(get_latex_service),
) -> CoverLetterGenerationService:
    """Get a cover letter generation service.

    Returns:
        CoverLetterGenerationService: Cover letter generation service
    """
    prompt_service = PromptService(user_repository=profile_repo)
    return CoverLetterGenerationService(
        cover_letter_repository=cover_letter_repo,
        portfolio_repository=portfolio_repo,
        profile_repository=profile_repo,
        resume_repository=resume_repo,
        llm_service=llm_service,
        prompt_service=prompt_service,
        latex_service=latex_service,
    )
