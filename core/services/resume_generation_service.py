"""Service for resume generation using LLM."""

import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from beanie import PydanticObjectId
from bson import json_util

from config.logging_config import get_logger
from core.exceptions.base import NotFoundException
from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.models.resume import Resume
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.profile_repository import ProfileRepository
from core.repositories.resume_repository import ResumeRepository
from core.services.latex_service import LatexService, get_latex_service
from core.services.llm_service import LLMService
from core.services.portfolio_service import PortfolioService
from core.services.profile_service import ProfileService
from core.services.prompt_service import PromptService

logger = get_logger(__name__)


class ResumeGenerationService:
    """Service for generating resume content using LLM and creating LaTeX documents."""

    def __init__(
        self,
        resume_repository: ResumeRepository,
        portfolio_repository: PortfolioRepository,
        profile_repository: ProfileRepository,
        profile_service: ProfileService = None,
        portfolio_service: PortfolioService = None,
        llm_service: Optional[LLMService] = None,
        prompt_service: Optional[PromptService] = None,
        latex_service: Optional[LatexService] = None,
    ):
        """
        Initialize the resume generation service.

        Args:
            resume_repository: Repository for accessing resume data
            portfolio_repository: Repository for accessing portfolio data
            profile_repository: Repository for accessing profile data
            profile_service: Service for profile operations (optional)
            portfolio_service: Service for portfolio operations (optional)
            llm_service: Service for LLM operations
            prompt_service: Service for loading and formatting prompts
            latex_service: Service for LaTeX document generation
        """
        self.resume_repository = resume_repository
        self.portfolio_repository = portfolio_repository
        self.profile_repository = profile_repository

        # Use provided services or create new ones
        from core.repositories.user_repository import UserRepository

        user_repository = UserRepository()

        self.profile_service = profile_service or ProfileService(
            profile_repository=profile_repository,
            user_repository=user_repository,
        )

        self.portfolio_service = portfolio_service or PortfolioService(
            portfolio_repository=portfolio_repository,
            user_repository=user_repository,
        )

        # Create services if not provided
        self.prompt_service = prompt_service
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
        self.logger.debug(f"Resume generation service configured for user {user_id}")

    async def get_resume_data(
        self, resume_id: PydanticObjectId
    ) -> Tuple[Resume, Profile, Portfolio]:
        """
        Get the resume, profile, and portfolio data for a resume.

        Args:
            resume_id: Resume ID

        Returns:
            Tuple of Resume, Profile, and Portfolio

        Raises:
            ValueError: If any required data is missing
        """
        # Get resume
        resume = await self.resume_repository.get_by_id(resume_id)
        if not resume:
            raise ValueError(f"Resume with ID {resume_id} not found")

        # Get profile
        profile = await self.profile_repository.get_by_id(resume.profile_id)
        if not profile:
            raise ValueError(f"Profile with ID {resume.profile_id} not found")

        # Get portfolio using portfolio service
        try:
            portfolio = await self.portfolio_service.get_portfolio_by_id(
                resume.portfolio_id
            )
            self.logger.debug(f"Retrieved portfolio with ID: {resume.portfolio_id}")
        except Exception as e:
            self.logger.error(f"Error retrieving portfolio: {e}")
            raise ValueError(
                f"Portfolio with ID {resume.portfolio_id} not found or could not be retrieved"
            )

        return resume, profile, portfolio

    def _convert_to_serializable(self, data):
        """
        Convert data to a serializable format.

        Args:
            data: The data to convert

        Returns:
            The data in a serializable format
        """
        try:
            # Import bson.json_util for handling MongoDB types
            from bson import ObjectId, json_util

            if data is None:
                return None
            elif isinstance(data, (PydanticObjectId, ObjectId)):
                # Convert ObjectId to string
                return str(data)
            elif hasattr(data, "model_dump"):
                # For Pydantic models, use model_dump()
                return data.model_dump()
            elif isinstance(data, (list, dict)):
                # Use json_util for safe serialization and deserialization
                serialized = json_util.loads(json_util.dumps(data))
                return serialized
            elif isinstance(data, (str, int, float, bool)):
                # Primitive types can be returned as is
                return data
            else:
                # For custom types, try string representation
                return str(data)

        except Exception as e:
            # Log error and return string representation
            self.logger.error(
                f"Error converting {type(data).__name__} to serializable format: {e}"
            )
            return str(data)

    async def _process_section(
        self,
        section_name: str,
        section_data: Any,
        resume: Resume,
        profile: Profile,
    ) -> Any:
        """
        Process a resume section based on profile preferences.

        Args:
            section_name: Name of the section to process
            section_data: Section data from portfolio
            resume: Resume object
            profile: Profile object

        Returns:
            Processed section content - can be JSON object or string
        """
        # Get processing preference for this section
        section_preference = "Process"  # Default to processing
        if profile.preferences and profile.preferences.section_preferences:
            section_preference = profile.preferences.section_preferences.get(
                section_name, "Process"
            )

        # Convert data to serializable form if needed
        section_data = self._convert_to_serializable(section_data)

        # If hardcode preference, return data directly (structured JSON)
        if section_preference.lower() == "hardcode":
            self.logger.info(f"Using hardcoded data for section: {section_name}")
            return section_data

        # Process with LLM - requesting JSON schema output
        context = {
            "section_data": section_data,
            "job_title": resume.job_title,
            "company_name": resume.company_name,
        }

        self.logger.info(
            f"Generating content for section: {section_name} using JSON schema"
        )

        # LLM will return content in JSON format
        return await self.llm_service.generate_section(
            section_name=section_name,
            context=context,
            job_description=resume.job_description or "",
            use_json_schema=True,  # Enable JSON schema output
        )

    async def generate_resume_content(
        self,
        resume_id: PydanticObjectId,
        regenerate_sections: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate or update content for a resume.

        Args:
            resume_id: Resume ID
            regenerate_sections: Optional list of section names to regenerate

        Returns:
            Generated resume content

        Raises:
            ValueError: If resume or profile is not found
        """
        # Get resume data
        resume, profile, portfolio = await self.get_resume_data(resume_id)

        # Configure LLM for user
        await self.configure_for_user(resume.user_id)

        # Initialize content dictionary if needed
        if not resume.content or not isinstance(resume.content, dict):
            resume.content = {}

        # Determine which sections to process
        sections_to_process = regenerate_sections or [
            "personal_information",
            "career_summary",
            "skills",
            "work_experience",
            "education",
            "projects",
            "awards",
            "publications",
        ]

        # Process each section
        for section_name in sections_to_process:
            try:
                # Get section data from portfolio
                section_data = None
                self.logger.debug(f"Processing section: {section_name}")

                if section_name == "personal_information":
                    # Get personal information from profile service
                    section_data = await self.profile_service.get_personal_information(
                        resume.user_id
                    )
                    self.logger.debug(
                        f"Retrieved personal information for user: {resume.user_id}"
                    )
                elif section_name == "career_summary":
                    # Get portfolio data from portfolio service
                    portfolio = await self.portfolio_service.get_portfolio_by_user_id(
                        resume.user_id
                    )
                    section_data = (
                        portfolio.career_summary
                        if portfolio and portfolio.career_summary
                        else None
                    )
                    self.logger.debug(
                        f"Retrieved career summary for user: {resume.user_id}"
                    )
                elif section_name == "skills":
                    # Get portfolio data from portfolio service
                    portfolio = await self.portfolio_service.get_portfolio_by_user_id(
                        resume.user_id
                    )
                    section_data = (
                        portfolio.skills if portfolio and portfolio.skills else []
                    )
                    self.logger.debug(f"Retrieved skills for user: {resume.user_id}")
                elif section_name == "work_experience":
                    # Get portfolio data from portfolio service
                    portfolio = await self.portfolio_service.get_portfolio_by_user_id(
                        resume.user_id
                    )
                    section_data = (
                        portfolio.work_experience
                        if portfolio and portfolio.work_experience
                        else []
                    )
                    self.logger.debug(
                        f"Retrieved work experience for user: {resume.user_id}"
                    )
                elif section_name == "education":
                    # Get portfolio data from portfolio service
                    portfolio = await self.portfolio_service.get_portfolio_by_user_id(
                        resume.user_id
                    )
                    section_data = (
                        portfolio.education if portfolio and portfolio.education else []
                    )
                    self.logger.debug(f"Retrieved education for user: {resume.user_id}")
                elif section_name == "projects":
                    # Get portfolio data from portfolio service
                    portfolio = await self.portfolio_service.get_portfolio_by_user_id(
                        resume.user_id
                    )
                    section_data = (
                        portfolio.projects if portfolio and portfolio.projects else []
                    )
                    self.logger.debug(f"Retrieved projects for user: {resume.user_id}")
                elif section_name == "awards":
                    # Get portfolio data from portfolio service
                    portfolio = await self.portfolio_service.get_portfolio_by_user_id(
                        resume.user_id
                    )
                    section_data = (
                        portfolio.awards if portfolio and portfolio.awards else []
                    )
                    self.logger.debug(f"Retrieved awards for user: {resume.user_id}")
                elif section_name == "publications":
                    # Get portfolio data from portfolio service
                    portfolio = await self.portfolio_service.get_portfolio_by_user_id(
                        resume.user_id
                    )
                    section_data = (
                        portfolio.publications
                        if portfolio and portfolio.publications
                        else []
                    )
                    self.logger.debug(
                        f"Retrieved publications for user: {resume.user_id}"
                    )
                elif section_name == "certifications":
                    # Get portfolio data from portfolio service
                    portfolio = await self.portfolio_service.get_portfolio_by_user_id(
                        resume.user_id
                    )
                    section_data = (
                        portfolio.certifications
                        if portfolio and portfolio.certifications
                        else []
                    )
                    self.logger.debug(
                        f"Retrieved certifications for user: {resume.user_id}"
                    )
                elif section_name in (
                    portfolio.custom_sections.enabled
                    if portfolio.custom_sections
                    else []
                ):
                    # Get portfolio data from portfolio service
                    portfolio = await self.portfolio_service.get_portfolio_by_user_id(
                        resume.user_id
                    )
                    section_data = portfolio.custom_sections if portfolio else None
                    self.logger.debug(
                        f"Retrieved custom sections for user: {resume.user_id}"
                    )

                # Skip if no data
                if section_data is None:
                    self.logger.warning(f"No data for section {section_name}")
                    continue

                # Process section
                try:
                    # Process the section to generate content
                    processed_content = await self._process_section(
                        section_name=section_name,
                        section_data=section_data,
                        resume=resume,
                        profile=profile,
                    )

                    # Update resume content with the processed section
                    resume.content[section_name] = processed_content
                    self.logger.debug(f"Successfully processed section: {section_name}")
                except Exception as section_error:
                    self.logger.error(
                        f"Error processing section {section_name}: {section_error}"
                    )
                    # Skip this section but continue with others
                    continue

            except Exception as e:
                self.logger.error(
                    f"Error generating content for section {section_name}: {e}"
                )
                # Continue with other sections even if one fails

        # Update resume
        resume.updated_at = datetime.now(timezone.utc)
        await self.resume_repository.update(resume.id, resume)
        self.logger.info(f"Updated resume content with {len(resume.content)} sections")

        return resume.content

    async def generate_latex(
        self,
        resume_id: PydanticObjectId,
    ) -> str:
        """
        Generate LaTeX code for a resume.

        Args:
            resume_id: Resume ID

        Returns:
            Resume LaTeX code

        Raises:
            ValueError: If resume, profile, or portfolio is not found
        """
        # Get resume data
        resume, profile, portfolio = await self.get_resume_data(resume_id)

        # Ensure content exists
        if not resume.content:
            await self.generate_resume_content(resume_id)

        # Generate LaTeX for resume using LaTeX service
        try:
            # Generate LaTeX for resume
            resume_latex = await self.latex_service.generate_resume_latex(
                resume=resume, profile=profile
            )

            return resume_latex

        except Exception as e:
            self.logger.error(f"Error generating LaTeX: {e}")
            raise ValueError(f"Failed to generate LaTeX: {str(e)}")

    async def compile_pdf(
        self,
        resume_id: PydanticObjectId,
    ) -> bytes:
        """
        Compile LaTeX to PDF for a resume.

        Args:
            resume_id: Resume ID

        Returns:
            bytes: PDF content

        Raises:
            ValueError: If resume, profile, or portfolio is not found
        """
        # Get resume data
        resume, profile, portfolio = await self.get_resume_data(resume_id)

        # Ensure content exists
        if not resume.content:
            await self.generate_resume_content(resume_id)

        # Generate and compile resume
        try:
            # Generate resume LaTeX
            resume_latex = await self.generate_latex(resume_id)

            # Compile to PDF
            pdf_bytes = await self.latex_service.compile_latex_to_pdf(
                resume_latex, is_cover_letter=False
            )

            # Verify PDF was generated successfully
            if not pdf_bytes or len(pdf_bytes) == 0:
                self.logger.error("PDF compilation returned empty bytes")
                raise ValueError("PDF compilation failed - empty result")

            # Log success
            self.logger.info(f"Successfully compiled PDF, size: {len(pdf_bytes)} bytes")

            # Save PDF to resume
            resume.resume_pdf = pdf_bytes
            resume.updated_at = datetime.now(timezone.utc)
            await self.resume_repository.update(resume.id, resume)

            return pdf_bytes
        except Exception as e:
            self.logger.error(f"Error compiling PDF: {e}")
            raise ValueError(f"Failed to compile PDF: {str(e)}")
