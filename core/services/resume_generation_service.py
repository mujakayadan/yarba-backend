"""Service for resume generation using LLM."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from beanie import PydanticObjectId

from config.logging_config import get_logger
from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.models.resume import Resume
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.profile_repository import ProfileRepository
from core.repositories.resume_repository import ResumeRepository
from core.services.llm_service import LLMService
from core.services.prompt_service import PromptService
from core.services.tex_service import TexService

logger = get_logger(__name__)


class ResumeGenerationService:
    """Service for generating resume content using LLM and creating LaTeX documents."""

    def __init__(
        self,
        resume_repository: ResumeRepository,
        portfolio_repository: PortfolioRepository,
        profile_repository: ProfileRepository,
        llm_service: Optional[LLMService] = None,
        prompt_service: Optional[PromptService] = None,
        tex_service: Optional[TexService] = None,
    ):
        """
        Initialize the resume generation service.

        Args:
            resume_repository: Repository for accessing resume data
            portfolio_repository: Repository for accessing portfolio data
            profile_repository: Repository for accessing profile data
            llm_service: Service for LLM operations
            prompt_service: Service for loading and formatting prompts
            tex_service: Service for LaTeX operations
        """
        self.resume_repository = resume_repository
        self.portfolio_repository = portfolio_repository
        self.profile_repository = profile_repository

        # Create services if not provided
        self.prompt_service = prompt_service
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

        # Get portfolio
        portfolio = await self.portfolio_repository.get_by_id(resume.portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio with ID {resume.portfolio_id} not found")

        return resume, profile, portfolio

    async def _process_section(
        self,
        section_name: str,
        section_data: Any,
        resume: Resume,
        profile: Profile,
    ) -> str:
        """
        Process a resume section based on profile preferences.

        Args:
            section_name: Name of the section to process
            section_data: Section data from portfolio
            resume: Resume object
            profile: Profile object

        Returns:
            Processed section content
        """
        # Get processing preference for this section
        section_preference = "Process"  # Default to processing
        if profile.preferences and profile.preferences.section_preferences:
            section_preference = profile.preferences.section_preferences.get(
                section_name, "Process"
            )

        # Convert data to serializable form if needed
        section_data = self._convert_to_serializable(section_data)

        # If hardcode preference, return data as is (serialized)
        if section_preference.lower() == "hardcode":
            if isinstance(section_data, (dict, list)):
                return json.dumps(section_data)
            return str(section_data)

        # Otherwise process with LLM
        context = {
            "section_data": section_data,
            "job_title": resume.job_title,
            "company_name": resume.company_name,
        }

        # Generate content with LLM
        return await self.llm_service.generate_section(
            section_name=section_name,
            context=context,
            job_description=resume.job_description or "",
        )

    def _convert_to_serializable(self, data):
        """
        Convert data to a serializable format.

        Args:
            data: The data to convert

        Returns:
            The data in a serializable format
        """
        if hasattr(data, "model_dump"):
            return data.model_dump()
        elif isinstance(data, list):
            return [self._convert_to_serializable(item) for item in data]
        elif isinstance(data, dict):
            return {k: self._convert_to_serializable(v) for k, v in data.items()}
        else:
            return data

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

                if section_name == "personal_information":
                    section_data = profile
                elif section_name == "career_summary":
                    section_data = await self.portfolio_repository.get_career_summary(
                        resume.user_id
                    )
                elif section_name == "skills":
                    section_data = await self.portfolio_repository.get_skills(
                        resume.user_id
                    )
                elif section_name == "work_experience":
                    section_data = await self.portfolio_repository.get_work_experience(
                        resume.user_id
                    )
                elif section_name == "education":
                    section_data = await self.portfolio_repository.get_education(
                        resume.user_id
                    )
                elif section_name == "projects":
                    section_data = await self.portfolio_repository.get_projects(
                        resume.user_id
                    )
                elif section_name == "awards":
                    section_data = await self.portfolio_repository.get_awards(
                        resume.user_id
                    )
                elif section_name == "publications":
                    section_data = await self.portfolio_repository.get_publications(
                        resume.user_id
                    )
                elif section_name == "certifications":
                    section_data = await self.portfolio_repository.get_certifications(
                        resume.user_id
                    )
                elif section_name in (
                    portfolio.custom_sections.enabled
                    if portfolio.custom_sections
                    else []
                ):
                    section_data = await self.portfolio_repository.get_custom_sections(
                        resume.user_id
                    )

                # Skip if no data
                if section_data is None:
                    self.logger.warning(f"No data for section {section_name}")
                    continue

                # Process section
                resume.content[section_name] = await self._process_section(
                    section_name=section_name,
                    section_data=section_data,
                    resume=resume,
                    profile=profile,
                )

                self.logger.debug(f"Generated content for section {section_name}")

            except Exception as e:
                self.logger.error(
                    f"Error generating content for section {section_name}: {e}"
                )
                # Continue with other sections even if one fails

        # Update resume
        resume.updated_at = datetime.now(timezone.utc)
        await self.resume_repository.update(resume.id, resume)

        return resume.content

    async def generate_cover_letter(
        self,
        resume_id: PydanticObjectId,
        regenerate: bool = False,
    ) -> str:
        """
        Generate a cover letter for a resume.

        Args:
            resume_id: Resume ID
            regenerate: Whether to regenerate the cover letter even if it exists

        Returns:
            Generated cover letter text

        Raises:
            ValueError: If resume, profile, or portfolio is not found
        """
        # Get resume data
        resume, profile, portfolio = await self.get_resume_data(resume_id)

        # Configure LLM for user
        await self.configure_for_user(resume.user_id)

        # Ensure resume content exists
        if not resume.content:
            await self.generate_resume_content(resume_id)

        # Generate cover letter
        try:
            cover_letter = await self.llm_service.generate_cover_letter(
                resume_content=resume.content,
                job_description=resume.job_description or "",
                company_name=resume.company_name or "",
                job_title=resume.job_title or "",
            )

            # Update resume
            resume.cover_letter_content = cover_letter
            resume.updated_at = datetime.now(timezone.utc)
            await self.resume_repository.update(resume.id, resume)

            return cover_letter

        except Exception as e:
            self.logger.error(f"Error generating cover letter: {e}")
            raise

    async def generate_latex(
        self,
        resume_id: PydanticObjectId,
    ) -> Tuple[str, str]:
        """
        Generate LaTeX code for a resume and cover letter.

        Args:
            resume_id: Resume ID

        Returns:
            Tuple of (resume_latex, cover_letter_latex)

        Raises:
            ValueError: If resume, profile, or portfolio is not found
        """
        # Get resume data
        resume, profile, portfolio = await self.get_resume_data(resume_id)

        # Ensure content exists
        if not resume.content:
            await self.generate_resume_content(resume_id)

        # Get LaTeX templates
        resume_template = await self.tex_service.get_default_preamble("resume_preamble")
        cover_letter_template = await self.tex_service.get_default_preamble(
            "cover_letter_preamble"
        )

        if not resume_template or not cover_letter_template:
            raise ValueError("LaTeX templates not found")

        # TODO: Implement actual LaTeX generation
        # This would combine the preamble and content into a complete LaTeX document
        # For now, we'll just return placeholders

        resume_latex = f"""
{resume_template.content}

\\begin{{document}}
% Generated resume content would go here
{resume.content.get("personal_information", "")}
\\end{{document}}
"""

        cover_letter_latex = f"""
{cover_letter_template.content}

\\begin{{document}}
% Generated cover letter content would go here
{resume.cover_letter_content}
\\end{{document}}
"""

        return resume_latex, cover_letter_latex
