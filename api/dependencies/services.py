"""Service dependencies for the API.

This module provides FastAPI dependencies for service layers.
"""

from typing import AsyncGenerator

from fastapi import Depends

from core.database.factory import (
    get_portfolio_repository,
    get_preamble_repository,
    get_profile_repository,
    get_resume_repository,
    get_tex_header_repository,
    get_tex_template_repository,
    get_user_repository,
)
from core.services.generator_service import GeneratorService
from core.services.job_service import JobService
from core.services.latex_service import LatexService
from core.services.llm_service import LLMService
from core.services.profile_service import ProfileService
from core.services.prompt_service import PromptService
from core.services.resume_service import ResumeService
from core.services.tex_service import TexService


async def get_tex_service(
    header_repo=Depends(get_tex_header_repository),
    template_repo=Depends(get_tex_template_repository),
    preamble_repo=Depends(get_preamble_repository),
) -> TexService:
    """Get a tex service.

    Args:
        header_repo: TeX header repository
        template_repo: TeX template repository
        preamble_repo: TeX preamble repository

    Returns:
        TexService: TeX service
    """
    return TexService(
        header_repository=header_repo,
        template_repository=template_repo,
        preamble_repository=preamble_repo,
    )


async def get_latex_service(
    preamble_repo=Depends(get_preamble_repository),
    header_repo=Depends(get_tex_header_repository),
    template_repo=Depends(get_tex_template_repository),
) -> LatexService:
    """Get a LaTeX service.

    Args:
        preamble_repo: LaTeX preamble repository
        header_repo: LaTeX header repository
        template_repo: LaTeX template repository

    Returns:
        LatexService: LaTeX service
    """
    return LatexService(
        preamble_repository=preamble_repo,
        header_repository=header_repo,
        template_repository=template_repo,
    )


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
) -> ResumeService:
    """Get a resume service.

    Returns:
        ResumeService: Resume service
    """
    return ResumeService(
        user_repository=user_repo,
        resume_repository=resume_repo,
    )


async def get_generator_service(
    resume_repo=Depends(get_resume_repository),
    profile_repo=Depends(get_profile_repository),
    portfolio_repo=Depends(get_portfolio_repository),
    llm_service: LLMService = Depends(get_llm_service),
    latex_service: LatexService = Depends(get_latex_service),
) -> GeneratorService:
    """Get a generator service.

    Returns:
        GeneratorService: Generator service
    """
    return GeneratorService(
        resume_repository=resume_repo,
        profile_repository=profile_repo,
        portfolio_repository=portfolio_repo,
        llm_service=llm_service,
        latex_service=latex_service,
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


# Add other services as needed
# async def get_resume_service() -> AsyncGenerator[ResumeService, None]:
#     """Get a resume service.
#
#     Yields:
#         ResumeService: Resume service instance
#     """
#     resume_repo = ResumeRepository()
#     profile_repo = ProfileRepository()
#     yield ResumeService(resume_repo, profile_repo)
