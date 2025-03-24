"""Service for cover letter generation using LLM."""

from datetime import datetime, timezone
from typing import Optional, Tuple

from beanie import PydanticObjectId

from config.logging_config import get_logger
from core.models.cover_letter import CoverLetter
from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.models.resume import Resume
from core.repositories.cover_letter_repository import CoverLetterRepository
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.profile_repository import ProfileRepository
from core.repositories.resume_repository import ResumeRepository
from core.services.llm_service import LLMService
from core.services.prompt_service import PromptService
from core.services.tex_service import TexService

logger = get_logger(__name__)


class CoverLetterGenerationService:
    """Service for generating cover letter content using LLM and creating LaTeX documents."""

    def __init__(
        self,
        cover_letter_repository: CoverLetterRepository,
        portfolio_repository: PortfolioRepository,
        profile_repository: ProfileRepository,
        resume_repository: ResumeRepository,
        llm_service: Optional[LLMService] = None,
        prompt_service: Optional[PromptService] = None,
        tex_service: Optional[TexService] = None,
    ):
        """
        Initialize the cover letter generation service.

        Args:
            cover_letter_repository: Repository for accessing cover letter data
            portfolio_repository: Repository for accessing portfolio data
            profile_repository: Repository for accessing profile data
            resume_repository: Repository for accessing resume data
            llm_service: Service for LLM operations
            prompt_service: Service for loading and formatting prompts
            tex_service: Service for LaTeX operations
        """
        self.cover_letter_repository = cover_letter_repository
        self.portfolio_repository = portfolio_repository
        self.profile_repository = profile_repository
        self.resume_repository = resume_repository

        # Create services if not provided
        self.prompt_service = prompt_service or PromptService(
            user_repository=ProfileRepository()
        )
        self.llm_service = llm_service or LLMService(
            profile_repository=profile_repository,
            prompt_service=self.prompt_service,
        )
        self.tex_service = tex_service or TexService()

        self.logger = get_logger(self.__class__.__name__)

    async def configure_for_user(self, user_id: PydanticObjectId) -> None:
        """
        Configure the service for a specific user.

        Args:
            user_id: User ID to configure for
        """
        await self.llm_service.configure_for_user(str(user_id))
        self.logger.debug(
            f"Cover letter generation service configured for user {user_id}"
        )

    async def get_cover_letter_data(
        self, cover_letter_id: PydanticObjectId
    ) -> Tuple[CoverLetter, Profile, Portfolio, Optional[Resume]]:
        """
        Get the cover letter, profile, portfolio, and resume data for a cover letter.

        Args:
            cover_letter_id: Cover letter ID

        Returns:
            Tuple of CoverLetter, Profile, Portfolio, and optional Resume

        Raises:
            ValueError: If any required data is missing
        """
        # Get cover letter
        cover_letter = await self.cover_letter_repository.get_by_id(cover_letter_id)
        if not cover_letter:
            raise ValueError(f"Cover letter with ID {cover_letter_id} not found")

        # Get profile
        profile = await self.profile_repository.get_by_id(cover_letter.profile_id)
        if not profile:
            raise ValueError(f"Profile with ID {cover_letter.profile_id} not found")

        # Get portfolio
        portfolio = None
        if cover_letter.portfolio_id:
            portfolio = await self.portfolio_repository.get_by_id(
                cover_letter.portfolio_id
            )
            if not portfolio:
                raise ValueError(
                    f"Portfolio with ID {cover_letter.portfolio_id} not found"
                )
        else:
            # Try to get default portfolio for user
            portfolio = await self.portfolio_repository.get_default_by_user_id(
                cover_letter.user_id
            )

        if not portfolio:
            raise ValueError(f"No portfolio found for user {cover_letter.user_id}")

        # Get resume if available
        resume = None
        if cover_letter.resume_id:
            resume = await self.resume_repository.get_by_id(cover_letter.resume_id)
            if not resume:
                self.logger.warning(
                    f"Resume with ID {cover_letter.resume_id} not found"
                )
                # Continue without resume, don't raise error

        return cover_letter, profile, portfolio, resume

    async def _build_basic_resume_content(
        self, profile: Profile, portfolio: Portfolio
    ) -> dict:
        """
        Build basic resume content from profile and portfolio.

        Args:
            profile: User profile
            portfolio: User portfolio

        Returns:
            dict: Basic resume content
        """
        return {
            "personal_information": {
                "name": getattr(profile, "full_name", ""),
                "email": getattr(profile, "email", ""),
                "phone": getattr(profile, "phone", ""),
                "address": getattr(profile, "address", ""),
                "linkedin": getattr(profile, "linkedin", ""),
                "github": getattr(profile, "github", ""),
                "website": getattr(profile, "website", ""),
            },
            "career_summary": getattr(portfolio, "career_summary", {}),
            "skills": getattr(portfolio, "skills", []),
            "work_experience": getattr(portfolio, "work_experience", []),
            "education": getattr(portfolio, "education", []),
            "projects": getattr(portfolio, "projects", []),
        }

    async def generate_cover_letter_content(
        self,
        cover_letter_id: PydanticObjectId,
        regenerate: bool = False,
    ) -> str:
        """
        Generate a cover letter content.

        Args:
            cover_letter_id: Cover letter ID
            regenerate: Whether to regenerate the content even if it exists

        Returns:
            Generated cover letter text

        Raises:
            ValueError: If cover letter, profile, or portfolio is not found
        """
        # Get cover letter data
        cover_letter, profile, portfolio, resume = await self.get_cover_letter_data(
            cover_letter_id
        )

        # If cover letter content exists and regenerate is False, return existing
        if cover_letter.cover_letter_content and not regenerate:
            return cover_letter.cover_letter_content

        # Configure LLM for user
        await self.configure_for_user(cover_letter.user_id)

        # Generate cover letter
        try:
            # Get resume content if available from linked resume, otherwise use cover letter content
            # or build basic content from profile and portfolio
            resume_content = {}

            if resume:
                # Use resume content if available
                resume_content = resume.content
            elif cover_letter.content:
                # Use cover letter's content
                resume_content = cover_letter.content
            else:
                # Build basic content
                resume_content = await self._build_basic_resume_content(
                    profile, portfolio
                )

            cover_letter_text = await self.llm_service.generate_cover_letter(
                resume_content=resume_content,
                job_description=cover_letter.job_description or "",
                company_name=cover_letter.company_name or "",
                job_title=cover_letter.job_title or "",
            )

            # Update cover letter
            cover_letter.cover_letter_content = cover_letter_text
            cover_letter.updated_at = datetime.now(timezone.utc)
            await self.cover_letter_repository.update(cover_letter)

            return cover_letter_text

        except Exception as e:
            self.logger.error(f"Error generating cover letter: {e}")
            raise

    async def generate_pdf(
        self,
        cover_letter_id: PydanticObjectId,
        regenerate: bool = False,
    ) -> bytes:
        """
        Generate a PDF for a cover letter.

        Args:
            cover_letter_id: Cover letter ID
            regenerate: Whether to regenerate the PDF even if it exists

        Returns:
            PDF bytes

        Raises:
            ValueError: If cover letter not found
        """
        # Get cover letter
        cover_letter, profile, portfolio, _ = await self.get_cover_letter_data(
            cover_letter_id
        )

        # If PDF exists and regenerate is False, return existing
        if cover_letter.cover_letter_pdf and not regenerate:
            return cover_letter.cover_letter_pdf

        # Ensure cover letter content exists
        if not cover_letter.cover_letter_content:
            await self.generate_cover_letter_content(cover_letter_id)
            # Reload cover letter to get updated content
            cover_letter = await self.cover_letter_repository.get_by_id(cover_letter_id)

        # Generate PDF
        try:
            # Generate LaTeX
            latex = await self.tex_service.generate_cover_letter_latex(
                cover_letter, profile, portfolio
            )

            # Compile to PDF
            pdf_bytes = await self.tex_service.compile_latex_to_pdf(latex)

            # Update cover letter
            cover_letter.cover_letter_pdf = pdf_bytes
            cover_letter.updated_at = datetime.now(timezone.utc)
            await self.cover_letter_repository.update(cover_letter)

            return pdf_bytes

        except Exception as e:
            self.logger.error(f"Error generating PDF: {e}")
            raise
