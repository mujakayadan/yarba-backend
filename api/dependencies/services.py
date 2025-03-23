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
    header_repo: get_tex_header_repository,
    template_repo: get_tex_template_repository,
    preamble_repo: get_preamble_repository,
) -> TexService:
    """
    Get the TeX service.

    Args:
        header_repo: TeX header repository
        template_repo: TeX template repository
        preamble_repo: Preamble repository

    Returns:
        TexService: TeX service
    """
    return TexService(
        header_repository=header_repo,
        template_repository=template_repo,
        preamble_repository=preamble_repo,
    )


async def get_latex_service(
    tex_service: TexService = Depends(get_tex_service),
) -> LatexService:
    """
    Get the LaTeX service.

    Args:
        tex_service: TeX service

    Returns:
        LatexService: LaTeX service
    """
    return LatexService(tex_service=tex_service)


async def get_prompt_service() -> PromptService:
    """
    Get the prompt service.

    Returns:
        PromptService: Prompt service
    """
    return PromptService()


async def get_llm_service(
    profile_repo: get_profile_repository,
    prompt_service: PromptService = Depends(get_prompt_service),
) -> LLMService:
    """
    Get the LLM service.

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
    """
    Get the job service.

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
    user_repo: get_user_repository,
    resume_repo: get_resume_repository,
) -> ResumeService:
    """
    Get the resume service.

    Args:
        resume_repo: Resume repository

    Returns:
        ResumeService: Resume service
    """
    return ResumeService(user_repository=user_repo, resume_repository=resume_repo)


async def get_generator_service(
    resume_repo: get_resume_repository,
    profile_repo: get_profile_repository,
    portfolio_repo: get_portfolio_repository,
    llm_service: LLMService = Depends(get_llm_service),
    latex_service: LatexService = Depends(get_latex_service),
) -> GeneratorService:
    """
    Get the generator service.

    Args:
        resume_repo: Resume repository
        profile_repo: Profile repository
        portfolio_repo: Portfolio repository
        llm_service: LLM service
        latex_service: LaTeX service

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


async def get_profile_service() -> AsyncGenerator[ProfileService, None]:
    """Get a profile service.

    Yields:
        ProfileService: Profile service instance
    """
    profile_repo = get_profile_repository()
    user_repo = get_user_repository()
    yield ProfileService(profile_repo, user_repo)


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
