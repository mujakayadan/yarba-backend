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
from core.services.latex_service import LatexService, get_latex_service
from core.services.llm_service import LLMService
from core.services.prompt_service import PromptService

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
        latex_service: Optional[LatexService] = None,
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
            latex_service: Service for LaTeX document generation
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

        # Initialize LaTeX service for document generation
        self.latex_service = latex_service or get_latex_service()

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
        llm_preferences: Optional[dict] = None,
    ) -> str:
        """
        Generate a cover letter content.

        Args:
            cover_letter_id: Cover letter ID
            regenerate: Whether to regenerate the content even if it exists
            llm_preferences: Optional LLM preferences to override defaults

        Returns:
            Generated cover letter text

        Raises:
            ValueError: If cover letter, profile, or portfolio is not found
        """
        # Get cover letter data
        cover_letter, profile, portfolio, resume = await self.get_cover_letter_data(
            cover_letter_id
        )

        # Check if we have a valid resume
        if not resume:
            raise ValueError(
                f"Required resume for cover letter {cover_letter_id} is not found"
            )

        # If cover letter content exists and regenerate is False, return existing content
        content = (
            cover_letter.content.get("cover_letter_content")
            if cover_letter.content
            else None
        )
        if content and not regenerate:
            return content

        # Configure LLM for user
        await self.configure_for_user(cover_letter.user_id)

        # Apply LLM preferences if provided
        if llm_preferences:
            self.logger.info(f"Applying custom LLM preferences: {llm_preferences}")
            self.llm_service.set_llm_preferences(llm_preferences)

        # Get resume content
        resume_data = None
        if resume:
            resume_data = resume.content if hasattr(resume, "content") else {}
        else:
            # If no resume is available, build basic content from profile and portfolio
            resume_data = await self._build_basic_resume_content(profile, portfolio)

        # Get job information from resume
        job_title = resume.job_title or "the position"
        company_name = resume.company_name or "your company"
        job_description = resume.job_description or ""

        # Load cover letter generation prompt
        self.logger.info(f"Generating cover letter content for {cover_letter_id}")
        prompt = await self.prompt_service.load_prompt(
            "cover_letter_generation",
            full_name=profile.full_name,
            job_title=job_title,
            company_name=company_name,
            job_description=job_description,
            resume_data=resume_data,
        )

        # Generate content
        try:
            content = await self.llm_service.generate_text(prompt)
        except Exception as e:
            self.logger.error(f"Error generating cover letter: {e}")
            raise ValueError(f"Error generating cover letter: {e}")

        # Update the cover letter with the generated content
        cover_letter.content = {"cover_letter_content": content}
        cover_letter.updated_at = datetime.now(timezone.utc)
        await self.cover_letter_repository.save(cover_letter)

        self.logger.info(
            f"Successfully generated cover letter content ({len(content)} chars)"
        )
        return content

    async def generate_latex(
        self,
        cover_letter_id: PydanticObjectId,
    ) -> str:
        """
        Generate LaTeX code for a cover letter.

        Args:
            cover_letter_id: Cover letter ID

        Returns:
            LaTeX code for the cover letter

        Raises:
            ValueError: If cover letter, profile, or portfolio is not found
        """
        # Get cover letter data
        cover_letter, profile, portfolio, resume = await self.get_cover_letter_data(
            cover_letter_id
        )

        # Check if we have a valid resume
        if not resume:
            raise ValueError(
                f"Required resume for cover letter {cover_letter_id} is not found"
            )

        # Ensure cover letter content exists
        content = (
            cover_letter.content.get("cover_letter_content")
            if cover_letter.content
            else None
        )
        if not content:
            await self.generate_cover_letter_content(cover_letter_id)
            # Reload cover letter to get updated content
            cover_letter = await self.cover_letter_repository.get_by_id(cover_letter_id)
            content = (
                cover_letter.content.get("cover_letter_content")
                if cover_letter.content
                else None
            )

            if not content:
                raise ValueError("Failed to generate cover letter content")

        # Generate LaTeX
        try:
            # Generate LaTeX using LatexService
            latex = await self.latex_service.generate_cover_letter_latex(
                cover_letter, profile, resume
            )

            return latex

        except Exception as e:
            self.logger.error(f"Error generating LaTeX: {e}")
            raise ValueError(f"Failed to generate LaTeX: {str(e)}")

    async def generate_pdf(
        self,
        cover_letter_id: PydanticObjectId,
        regenerate: bool = False,
    ) -> bytes:
        """
        Generate PDF for a cover letter.

        Args:
            cover_letter_id: Cover letter ID
            regenerate: Force regeneration even if PDF exists

        Returns:
            PDF bytes

        Raises:
            ValueError: If cover letter not found
        """
        # Get cover letter
        cover_letter, profile, portfolio, resume = await self.get_cover_letter_data(
            cover_letter_id
        )

        # Check if we have a valid resume
        if not resume:
            raise ValueError(
                f"Required resume for cover letter {cover_letter_id} is not found"
            )

        # If PDF exists in S3 and regenerate is False, get and return existing
        if cover_letter.cover_letter_pdf_key and not regenerate:
            # Get the PDF from S3
            try:
                from utils.storage import get_storage_provider

                storage_provider = get_storage_provider()

                # Get the URL
                pdf_url = storage_provider.get_url(cover_letter.cover_letter_pdf_key)

                # If URL is available, download the content
                if pdf_url:
                    import httpx

                    async with httpx.AsyncClient() as client:
                        response = await client.get(pdf_url)
                        if response.status_code == 200:
                            return response.content
            except Exception as e:
                self.logger.error(f"Error retrieving PDF from storage: {e}")
                # Continue to regenerate PDF if retrieval fails

        # Ensure cover letter content exists
        content = (
            cover_letter.content.get("cover_letter_content")
            if cover_letter.content
            else None
        )
        if not content:
            await self.generate_cover_letter_content(cover_letter_id)
            # Reload cover letter to get updated content
            cover_letter = await self.cover_letter_repository.get_by_id(cover_letter_id)

        # Generate PDF
        try:
            # Generate LaTeX using the generate_latex method
            latex = await self.generate_latex(cover_letter_id)

            # Compile to PDF using LatexService
            pdf_bytes = await self.latex_service.compile_latex_to_pdf(
                latex, is_cover_letter=True
            )

            # Save PDF to S3
            try:
                from utils.storage import get_storage_provider

                storage_provider = get_storage_provider()
                pdf_key = await storage_provider.save_cover_letter_pdf(
                    pdf_bytes, str(cover_letter_id)
                )

                # Update cover letter with S3 key
                cover_letter.cover_letter_pdf_key = pdf_key
                cover_letter.updated_at = datetime.now(timezone.utc)
                await self.cover_letter_repository.update(cover_letter)

                self.logger.info(f"Saved cover letter PDF to storage: {pdf_key}")
            except Exception as storage_error:
                self.logger.error(f"Error saving PDF to storage: {storage_error}")
                # Continue to return the PDF bytes even if saving to S3 fails

            return pdf_bytes

        except Exception as e:
            self.logger.error(f"Error generating PDF: {e}")
            raise
