"""Service dependencies for FastAPI."""

from fastapi import Depends

from core.services.generator_service import GeneratorService
from core.services.latex_service import LatexService
from core.services.llm_service import LLMService
from core.services.prompt_service import PromptService
from core.services.resume_service import ResumeService
from core.services.tex_service import TexService

from .database import (
    PortfolioRepo,
    PreambleRepo,
    ProfileRepo,
    ResumeRepo,
    TexHeaderRepo,
    TexTemplateRepo,
)


async def get_tex_service(
    header_repo: TexHeaderRepo,
    template_repo: TexTemplateRepo,
    preamble_repo: PreambleRepo,
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
    profile_repo: ProfileRepo,
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


async def get_resume_service(
    resume_repo: ResumeRepo,
) -> ResumeService:
    """
    Get the resume service.

    Args:
        resume_repo: Resume repository

    Returns:
        ResumeService: Resume service
    """
    return ResumeService(resume_repository=resume_repo)


async def get_generator_service(
    resume_repo: ResumeRepo,
    profile_repo: ProfileRepo,
    portfolio_repo: PortfolioRepo,
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
