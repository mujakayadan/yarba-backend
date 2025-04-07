"""Service for resume generation using LLM."""

import json
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

    def _generate_proper_title(self, company_name: str, job_title: str) -> str:
        """
        Generate a properly formatted title from company_name and job_title.

        Args:
            company_name: Company name with lowercase and underscores
            job_title: Job title with lowercase and underscores

        Returns:
            Properly formatted title
        """
        if not company_name and not job_title:
            return "My Resume"

        # Convert underscores to spaces and capitalize words
        formatted_company = (
            " ".join(word.capitalize() for word in company_name.split("_"))
            if company_name
            else ""
        )
        formatted_job = (
            " ".join(word.capitalize() for word in job_title.split("_"))
            if job_title
            else ""
        )

        # Combine them with a space if both exist
        if formatted_company and formatted_job:
            return f"{formatted_company} {formatted_job}"
        elif formatted_company:
            return formatted_company
        else:
            return formatted_job

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
        # Check if section data exists
        if section_data is None:
            self.logger.warning(f"No data for section {section_name}")
            return None

        # Get processing preference for this section
        section_preference = "Process"  # Default to processing
        if profile.preferences and profile.preferences.section_preferences:
            section_preference = profile.preferences.section_preferences.get(
                section_name, "Process"
            )

        # Convert data to serializable form if needed
        section_data = self._convert_to_serializable(section_data)
        self.logger.debug(
            f"Section data after serialization ({section_name}): {type(section_data).__name__}"
        )

        # If hardcode preference, use the data as is
        if section_preference.lower() == "hardcode":
            self.logger.info(f"Using hardcoded data for section: {section_name}")
            return section_data

        # Prepare context for LLM
        context = {
            "section_data": section_data,
            "job_title": resume.job_title,
            "company_name": resume.company_name,
        }

        self.logger.info(
            f"Generating content for section: {section_name} using JSON schema"
        )

        # LLM will return content in JSON format
        try:
            result = await self.llm_service.generate_section(
                section_name=section_name,
                context=context,
                job_description=resume.job_description or "",
                use_json_schema=True,  # Enable JSON schema output
            )
            self.logger.debug(
                f"LLM generated result for {section_name}: {result[:100]}..."
            )
            return result
        except Exception as e:
            self.logger.error(
                f"Error generating content with LLM for section {section_name}: {e}"
            )
            # In case of error, return the original data
            return section_data

    async def _collect_section_data(self, resume: Resume) -> Dict[str, Any]:
        """
        Collect section data from portfolio for all standard resume sections.

        Args:
            resume: Resume object

        Returns:
            Dictionary of section data by section name
        """
        sections_data = {}
        user_id = resume.user_id

        # Get personal information
        try:
            sections_data["personal_information"] = (
                await self.profile_service.get_personal_information(user_id)
            )
        except Exception as e:
            self.logger.error(f"Error getting personal information: {e}")

        # Get portfolio for all other sections
        try:
            portfolio = await self.portfolio_service.get_portfolio_by_user_id(user_id)

            if portfolio:
                # Standard sections from portfolio
                section_mappings = {
                    "career_summary": portfolio.career_summary,
                    "skills": portfolio.skills,
                    "work_experience": portfolio.work_experience,
                    "education": portfolio.education,
                    "projects": portfolio.projects,
                    "awards": portfolio.awards,
                    "publications": portfolio.publications,
                    "certifications": portfolio.certifications,
                }

                # Add sections that have data
                for section_name, section_data in section_mappings.items():
                    if section_data:  # Skip empty sections
                        sections_data[section_name] = section_data

                # Add enabled custom sections
                if portfolio.custom_sections and portfolio.custom_sections.enabled:
                    for custom_section in portfolio.custom_sections.enabled:
                        if custom_section not in sections_data:
                            sections_data[custom_section] = portfolio.custom_sections

        except Exception as e:
            self.logger.error(f"Error collecting portfolio sections: {e}")

        return sections_data

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

        # Update resume title with properly formatted version
        if resume.company_name or resume.job_title:
            resume.title = self._generate_proper_title(
                resume.company_name, resume.job_title
            )
            self.logger.debug(f"Updated resume title to: {resume.title}")

        # Initialize content dictionary if needed
        if not resume.content or not isinstance(resume.content, dict):
            resume.content = {}

        # Collect all section data at once
        sections_data = await self._collect_section_data(resume)
        self.logger.info(f"Collected data for {len(sections_data)} sections")

        # Determine which sections to process
        if regenerate_sections:
            # Process only specified sections
            sections_to_process = [s for s in regenerate_sections if s in sections_data]
        else:
            # Process all available sections
            sections_to_process = list(sections_data.keys())

        # Keep track of processed sections
        processed_sections = set()

        # Process each section
        for section_name in sections_to_process:
            try:
                section_data = sections_data.get(section_name)

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
                    processed_sections.add(section_name)
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

        # Log processed sections
        self.logger.info(f"Processed sections: {processed_sections}")

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
        Generate LaTeX for a resume.

        Args:
            resume_id: Resume ID

        Returns:
            str: LaTeX content

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
                resume=resume, profile=profile, template_id=resume.template_id
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
