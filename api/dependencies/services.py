"""Service dependencies for the API.

This module provides FastAPI dependencies for service layers.
"""

from fastapi import Depends

from core.database.factory import (
    get_cover_letter_repository,
    get_portfolio_repository,
    get_portfolio_site_token_repository,
    get_profile_repository,
    get_resume_repository,
    get_user_repository,
)
from core.job_extractor.extract_job import JobExtractor
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.portfolio_site_token_repository import (
    PortfolioSiteTokenRepository,
)
from core.repositories.portfolio_website_repository import PortfolioWebsiteRepository
from core.repositories.profile_repository import ProfileRepository
from core.repositories.resume_repository import ResumeRepository
from core.repositories.user_repository import UserRepository
from core.services.aws_deployment_service import AWSDeploymentService
from core.services.cover_letter_generation_service import CoverLetterGenerationService
from core.services.cover_letter_service import CoverLetterService
from core.services.email_resume_service import (
    EmailResumeService,
    build_email_resume_service,
)
from core.services.job_service import JobService
from core.services.latex_service import LatexService
from core.services.llm_service import LLMService
from core.services.portfolio_service import PortfolioService
from core.services.portfolio_website_service import PortfolioWebsiteService
from core.services.profile_service import ProfileService
from core.services.prompt_service import PromptService
from core.services.public_portfolio_service import PublicPortfolioService
from core.services.resume_generation_service import ResumeGenerationService
from core.services.resume_service import ResumeService
from core.services.website_generator_service import WebsiteGeneratorService


def get_public_portfolio_service(
    token_repo: PortfolioSiteTokenRepository = Depends(
        get_portfolio_site_token_repository
    ),
    portfolio_repo: PortfolioRepository = Depends(get_portfolio_repository),
    profile_repo: ProfileRepository = Depends(get_profile_repository),
) -> PublicPortfolioService:
    """Get the public portfolio content service."""
    return PublicPortfolioService(
        token_repository=token_repo,
        portfolio_repository=portfolio_repo,
        profile_repository=profile_repo,
    )


def get_portfolio_service(
    portfolio_repo: PortfolioRepository = Depends(get_portfolio_repository),
    user_repo: UserRepository = Depends(get_user_repository),
) -> PortfolioService:
    """Get a portfolio service.

    Returns:
        PortfolioService: Portfolio service
    """
    return PortfolioService(
        portfolio_repository=portfolio_repo,
        user_repository=user_repo,
    )


async def get_latex_service(
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
) -> LatexService:
    """Get a LaTeX service.

    Args:
        portfolio_service: The portfolio service dependency.

    Returns:
        LatexService: LaTeX service
    """
    return LatexService(portfolio_service=portfolio_service)


async def get_prompt_service() -> PromptService:
    """Get a prompt service.

    Returns:
        PromptService: Prompt service
    """
    return PromptService()


async def get_llm_service(
    profile_repo=Depends(get_profile_repository),
) -> LLMService:
    """Get a LLM service.

    Args:
        profile_repo: Profile repository

    Returns:
        LLMService: LLM service
    """
    return LLMService(
        profile_repository=profile_repo,
    )


async def get_job_extractor() -> JobExtractor:
    """Get a JobExtractor instance.

    Returns:
        JobExtractor: An instance of the job extractor.
    """
    return JobExtractor()


async def get_job_service(
    llm_service: LLMService = Depends(get_llm_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    job_extractor: JobExtractor = Depends(get_job_extractor),
) -> JobService:
    """Get a job service.

    Args:
        llm_service: LLM service
        prompt_service: Prompt service
        job_extractor: JobExtractor instance

    Returns:
        JobService: Job service
    """
    return JobService(
        llm_service=llm_service,
        prompt_service=prompt_service,
        job_extractor=job_extractor,
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
    profile_repo: ProfileRepository = Depends(get_profile_repository),
    user_repo: UserRepository = Depends(get_user_repository),
) -> ProfileService:
    """Get a profile service.

    Args:
        profile_repo: Profile repository
        user_repo: User repository

    Returns:
        ProfileService: Profile service instance
    """
    return ProfileService(profile_repo, user_repo)


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
    resume_repo: ResumeRepository = Depends(get_resume_repository),
    portfolio_repo: PortfolioRepository = Depends(get_portfolio_repository),
    profile_repo: ProfileRepository = Depends(get_profile_repository),
    # Inject all required dependencies explicitly
    prompt_service: PromptService = Depends(get_prompt_service),
    profile_service: ProfileService = Depends(get_profile_service),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
    llm_service: LLMService = Depends(get_llm_service),
    latex_service: LatexService = Depends(get_latex_service),
    job_service: JobService = Depends(get_job_service),
) -> ResumeGenerationService:
    """Get a resume generation service.

    Returns:
        ResumeGenerationService: Resume generation service instance with all dependencies injected.
    """
    # No longer need to create PromptService here, it's injected
    return ResumeGenerationService(
        resume_repository=resume_repo,
        portfolio_repository=portfolio_repo,
        profile_repository=profile_repo,
        prompt_service=prompt_service,
        profile_service=profile_service,
        portfolio_service=portfolio_service,
        llm_service=llm_service,
        latex_service=latex_service,
        job_service=job_service,
    )


def get_cover_letter_generation_service(
    cover_letter_repo=Depends(get_cover_letter_repository),
    portfolio_repo=Depends(get_portfolio_repository),
    profile_repo=Depends(get_profile_repository),
    resume_repo=Depends(get_resume_repository),
    llm_service=Depends(get_llm_service),
    latex_service=Depends(get_latex_service),
    prompt_service: PromptService = Depends(get_prompt_service),
) -> CoverLetterGenerationService:
    """Get a cover letter generation service.

    Returns:
        CoverLetterGenerationService: Cover letter generation service
    """
    return CoverLetterGenerationService(
        cover_letter_repository=cover_letter_repo,
        portfolio_repository=portfolio_repo,
        profile_repository=profile_repo,
        resume_repository=resume_repo,
        llm_service=llm_service,
        prompt_service=prompt_service,
        latex_service=latex_service,
    )


async def get_portfolio_website_repository() -> PortfolioWebsiteRepository:
    """Get a portfolio website repository.

    Returns:
        PortfolioWebsiteRepository: Portfolio website repository
    """
    return PortfolioWebsiteRepository()


async def get_aws_deployment_service() -> AWSDeploymentService:
    """Get AWS deployment service.

    Returns:
        AWSDeploymentService: AWS deployment service
    """
    return AWSDeploymentService()


async def get_website_generator_service() -> WebsiteGeneratorService:
    """Get website generator service.

    Returns:
        WebsiteGeneratorService: Website generator service
    """
    return WebsiteGeneratorService()


async def get_portfolio_website_service(
    website_repo: PortfolioWebsiteRepository = Depends(
        get_portfolio_website_repository
    ),
    portfolio_repo: PortfolioRepository = Depends(get_portfolio_repository),
    user_repo: UserRepository = Depends(get_user_repository),
    profile_repo: ProfileRepository = Depends(get_profile_repository),
    aws_service: AWSDeploymentService = Depends(get_aws_deployment_service),
    generator_service: WebsiteGeneratorService = Depends(get_website_generator_service),
) -> PortfolioWebsiteService:
    """Get portfolio website service.

    Args:
        website_repo: Portfolio website repository
        portfolio_repo: Portfolio repository
        user_repo: User repository
        profile_repo: Profile repository
        aws_service: AWS deployment service
        generator_service: Website generator service

    Returns:
        PortfolioWebsiteService: Portfolio website service
    """
    return PortfolioWebsiteService(
        website_repository=website_repo,
        portfolio_repository=portfolio_repo,
        user_repository=user_repo,
        profile_repository=profile_repo,
        aws_deployment_service=aws_service,
        website_generator_service=generator_service,
    )


def get_email_resume_service() -> EmailResumeService:
    """Get the email-to-resume orchestration service."""
    return build_email_resume_service()
