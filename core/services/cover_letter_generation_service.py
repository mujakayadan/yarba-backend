"""Service for cover letter generation using LLM."""

import json
from datetime import UTC, datetime

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
from core.utils.object_id import require_object_id

logger = get_logger(__name__)


class CoverLetterGenerationService:
    """Service for generating cover letter content using LLM and creating LaTeX documents."""

    def __init__(
        self,
        cover_letter_repository: CoverLetterRepository,
        portfolio_repository: PortfolioRepository,
        profile_repository: ProfileRepository,
        resume_repository: ResumeRepository,
        llm_service: LLMService | None = None,
        prompt_service: PromptService | None = None,
        latex_service: LatexService | None = None,
    ):
        """Initialize the cover letter generation service.

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
        from core.repositories.user_repository import UserRepository

        user_repository = UserRepository()

        # Initialize prompt service first since the LLM service depends on it
        self.prompt_service = prompt_service or PromptService(
            user_repository=user_repository
        )

        # Initialize LLM service
        self.llm_service = llm_service or LLMService(
            profile_repository=profile_repository,
        )

        # Initialize LaTeX service for document generation
        self.latex_service = latex_service or get_latex_service()

        self.logger = get_logger(self.__class__.__name__)

    async def configure_for_user(self, user_id: PydanticObjectId) -> None:
        """Configure the service for a specific user.

        Args:
            user_id: User ID to configure for
        """
        await self.llm_service.configure_for_user(user_id)
        self.logger.debug(
            f"Cover letter generation service configured for user {user_id}"
        )

    async def get_cover_letter_data(
        self, cover_letter_id: PydanticObjectId
    ) -> tuple[CoverLetter, Profile, Portfolio, Resume | None]:
        """Get the cover letter, profile, portfolio, and resume data for a cover letter.

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
        profile = await self.profile_repository.get_by_id(
            require_object_id(cover_letter.profile_id)
        )
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
            portfolio = await self.portfolio_repository.get_by_user_id(
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
        """Build basic resume content from profile and portfolio.

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
        """Generate content for a cover letter.

        Args:
            cover_letter_id: Cover letter ID
            regenerate: Whether to regenerate content even if it already exists

        Returns:
            Generated cover letter content

        Raises:
            ValueError: If cover letter, resume, or profile is not found
        """
        # Get cover letter data
        cover_letter, profile, portfolio, resume = await self.get_cover_letter_data(
            cover_letter_id
        )

        # Configure LLM for user
        await self.configure_for_user(cover_letter.user_id)

        # Set cover_letter_id for cost tracking in LLM service
        self.llm_service.current_cover_letter_id = cover_letter_id

        # Get resume content
        resume_data = None
        if resume:
            resume_data = resume.content if hasattr(resume, "content") else {}
        else:
            # If no resume is available, build basic content from profile and portfolio
            resume_data = await self._build_basic_resume_content(profile, portfolio)

        # Get job information from resume when available
        job_title = (resume.job_title if resume else None) or "the position"
        company_name = (resume.company_name if resume else None) or "your company"
        job_description = (resume.job_description if resume else None) or ""

        # Get candidate's full name
        candidate_name = "Candidate"
        if profile:
            if (
                hasattr(profile, "personal_information")
                and profile.personal_information
            ):
                candidate_name = getattr(
                    profile.personal_information, "full_name", "Candidate"
                )
            elif hasattr(profile, "full_name"):
                candidate_name = profile.full_name

        # Get cover letter prompt
        self.logger.info(f"Generating cover letter content for {cover_letter_id}")
        try:
            # Get the cover letter prompt
            prompt_text = await self.prompt_service.get_cover_letter_prompt()

            # Get system prompt
            system_prompt = await self.prompt_service.get_system_prompt()

            # Create the full prompt
            # Include life story if available
            life_story = ""
            if profile and hasattr(profile, "life_story") and profile.life_story:
                life_story = f"""
Life Story:
{profile.life_story}
"""

            full_prompt = f"""
Job Title: {job_title}
Company Name: {company_name}
Job Description:
{job_description}

Resume Data:
{resume_data}

Candidate Name: {candidate_name}
{life_story}
{prompt_text}
"""
            # Generate content using get_completion method
            llm_response_dict = await self.llm_service.get_completion(
                prompt=full_prompt,
                system_prompt=system_prompt,
            )
            self.logger.info(
                f"LLM service response dictionary for cover letter {cover_letter_id}: {str(llm_response_dict)[:1000]}"
            )

            actual_cover_letter_json_str = None
            if (
                isinstance(llm_response_dict, dict)
                and "llm_output" in llm_response_dict
            ):
                actual_cover_letter_json_str = llm_response_dict["llm_output"]
                if not isinstance(actual_cover_letter_json_str, str):
                    self.logger.error(
                        f"LLM output's 'llm_output' field is not a string: {type(actual_cover_letter_json_str)}. Using string of full response dict as fallback."
                    )
                    actual_cover_letter_json_str = str(llm_response_dict)  # Fallback
            else:
                self.logger.warning(
                    f"Could not find 'llm_output' in LLM response dict or response is not a dict. Using string representation of response. Response: {str(llm_response_dict)[:500]}"
                )
                actual_cover_letter_json_str = str(llm_response_dict)  # Fallback

            self.logger.info(
                f"Extracted cover_letter JSON string for {cover_letter_id}: {str(actual_cover_letter_json_str)[:500]}"
            )

            # Parse the JSON string from LLM and extract the full document text
            try:
                parsed_content = json.loads(actual_cover_letter_json_str)
                full_document_text = parsed_content.get("full_document", "")
                if not full_document_text:
                    self.logger.warning(
                        f"'full_document' key missing or empty in parsed LLM response for {cover_letter_id}. Response: {actual_cover_letter_json_str}"
                    )
                    # Fallback: use the raw string if parsing/extraction fails
                    full_document_text = actual_cover_letter_json_str
            except json.JSONDecodeError:
                self.logger.error(
                    f"Failed to decode JSON from LLM response for {cover_letter_id}. Response: {actual_cover_letter_json_str}"
                )
                # Fallback: use the raw string if JSON is invalid
                full_document_text = actual_cover_letter_json_str

            # Update the cover letter with the generated content
            cover_letter.content = (
                full_document_text  # Store the extracted text directly
            )
            cover_letter.updated_at = datetime.now(UTC)
            await cover_letter.save()

            self.logger.info(
                f"Successfully generated cover letter content ({len(full_document_text)} chars)"
            )
            return str(full_document_text)  # Return the extracted text string

        except Exception as e:
            self.logger.error(f"Error generating cover letter: {e}")
            raise ValueError(f"Error generating cover letter: {e}")

    async def generate_latex(
        self,
        cover_letter_id: PydanticObjectId,
    ) -> str:
        """Generate LaTeX code for a cover letter.

        Args:
            cover_letter_id: Cover letter ID

        Returns:
            LaTeX code for the cover letter

        Raises:
            ValueError: If cover letter, profile, or portfolio is not found
        """
        try:
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
            content_exists = bool(
                cover_letter.content
            )  # Check if string is not None or empty

            if not content_exists:
                self.logger.info(
                    f"No content found, generating content for cover letter: {cover_letter_id}"
                )
                await self.generate_cover_letter_content(cover_letter_id)
                # Reload cover letter to get updated content
                reloaded_cover_letter = await self.cover_letter_repository.get_by_id(
                    cover_letter_id
                )
                if not reloaded_cover_letter:
                    raise ValueError(
                        f"Cover letter with ID {cover_letter_id} not found after content generation"
                    )
                cover_letter = reloaded_cover_letter
                content_exists = bool(cover_letter.content)  # Re-check

                if not content_exists:
                    raise ValueError(
                        "Failed to generate cover letter content after attempt"
                    )

            # Generate LaTeX
            self.logger.info(f"Generating LaTeX for cover letter: {cover_letter_id}")
            latex = await self.latex_service.generate_cover_letter_latex(
                cover_letter, profile, resume
            )

            if not latex:
                raise ValueError("LaTeX generation produced empty content")

            self.logger.info(
                f"Successfully generated LaTeX for cover letter: {cover_letter_id}"
            )
            return latex

        except Exception as e:
            self.logger.error(f"Error generating LaTeX: {e}")
            raise ValueError(f"Failed to generate LaTeX: {str(e)}")

    async def generate_pdf(
        self,
        cover_letter_id: PydanticObjectId,
    ) -> bytes:
        """Generate PDF for a cover letter.

        Args:
            cover_letter_id: Cover letter ID

        Returns:
            PDF bytes

        Raises:
            ValueError: If cover letter not found
        """
        try:
            # Get cover letter
            cover_letter, profile, portfolio, resume = await self.get_cover_letter_data(
                cover_letter_id
            )

            # Check if we have a valid resume
            if not resume:
                raise ValueError(
                    f"Required resume for cover letter {cover_letter_id} is not found"
                )

            # Ensure cover letter content exists
            content_exists = bool(
                cover_letter.content
            )  # Check if string is not None or empty

            if not content_exists:
                self.logger.info(
                    f"No content found, generating content for cover letter: {cover_letter_id}"
                )
                await self.generate_cover_letter_content(cover_letter_id)
                # Reload cover letter to get updated content
                reloaded_cover_letter = await self.cover_letter_repository.get_by_id(
                    cover_letter_id
                )
                if not reloaded_cover_letter:
                    raise ValueError(
                        f"Cover letter with ID {cover_letter_id} not found after content generation"
                    )
                cover_letter = reloaded_cover_letter
                content_exists = bool(cover_letter.content)  # Re-check

                if not content_exists:
                    raise ValueError(
                        "Failed to generate cover letter content after attempt"
                    )

            # Generate PDF
            # Generate LaTeX using the generate_latex method
            self.logger.info(f"Generating LaTeX for cover letter: {cover_letter_id}")
            latex = await self.generate_latex(cover_letter_id)

            # Compile to PDF using LatexService
            self.logger.info(
                f"Compiling LaTeX to PDF for cover letter: {cover_letter_id}"
            )
            pdf_bytes = await self.latex_service.compile_latex_to_pdf(
                latex,
                is_cover_letter=True,
                company_name=resume.company_name,
                job_title=resume.job_title,
            )

            if not pdf_bytes or len(pdf_bytes) == 0:
                self.logger.error("PDF compilation returned empty bytes")
                raise ValueError("PDF compilation failed - empty result")

            # Save PDF to S3
            try:
                from utils.storage import get_storage_provider

                storage_provider = get_storage_provider()
                pdf_key = await storage_provider.save_cover_letter_pdf(
                    pdf_bytes, str(cover_letter_id)
                )

                # Update cover letter with S3 key
                cover_letter.cover_letter_pdf_key = pdf_key
                cover_letter.updated_at = datetime.now(UTC)
                await cover_letter.save()

                self.logger.info(f"Saved cover letter PDF to storage: {pdf_key}")
            except Exception as storage_error:
                self.logger.error(f"Error saving PDF to storage: {storage_error}")
                # Continue to return the PDF bytes even if saving to S3 fails

            return pdf_bytes

        except Exception as e:
            self.logger.error(f"Error generating PDF: {e}")
            raise ValueError(f"Failed to generate PDF: {str(e)}")
