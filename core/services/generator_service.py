"""Service for document generation using DocumentGenerator."""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from beanie import PydanticObjectId
from fastapi import HTTPException

from config.logging_config import get_logger
from config.settings import Settings
from core.models.cover_letter import CoverLetter
from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.models.resume import Resume
from core.repositories.cover_letter_repository import CoverLetterRepository
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.profile_repository import ProfileRepository
from core.repositories.resume_repository import ResumeRepository
from core.services.latex_service import LatexService
from core.services.llm_service import LLMService

logger = get_logger(__name__)
settings = Settings()


class GeneratorService:
    """
    Service for generating documents (resumes and cover letters).
    This service consolidates functionality from previous Generator classes.
    """

    def __init__(
        self,
        resume_repository: ResumeRepository,
        profile_repository: ProfileRepository,
        portfolio_repository: PortfolioRepository,
        cover_letter_repository: CoverLetterRepository,
        llm_service: LLMService,
        latex_service: LatexService,
    ):
        """
        Initialize the document generator service.

        Args:
            resume_repository: Repository for accessing resume data
            profile_repository: Repository for accessing profile data
            portfolio_repository: Repository for accessing portfolio data
            cover_letter_repository: Repository for accessing cover letter data
            llm_service: Service for LLM operations
            latex_service: Service for LaTeX operations
        """
        self.resume_repository = resume_repository
        self.profile_repository = profile_repository
        self.portfolio_repository = portfolio_repository
        self.cover_letter_repository = cover_letter_repository
        self.llm_service = llm_service
        self.latex_service = latex_service
        self.logger = get_logger(self.__class__.__name__)

    async def _get_user_data(
        self, user_id: PydanticObjectId, resume_id: Optional[PydanticObjectId] = None
    ) -> Tuple[Optional[Resume], Profile, Portfolio]:
        """
        Get profile and portfolio data for a user, and optionally a resume.

        Args:
            user_id: User ID
            resume_id: Optional resume ID

        Returns:
            Tuple of Resume (or None), Profile, and Portfolio

        Raises:
            ValueError: If any required data is missing
        """
        # Get profile
        profile = await self.profile_repository.get_by_user_id(user_id)
        if not profile:
            raise ValueError(f"Profile not found for user {user_id}")

        # Get portfolio
        portfolio = await self.portfolio_repository.get_by_user_id(user_id)
        if not portfolio:
            raise ValueError(f"Portfolio not found for user {user_id}")

        # Get resume if resume_id is provided
        resume = None
        if resume_id:
            resume = await self.resume_repository.get_by_id(resume_id)
            if not resume:
                raise ValueError(f"Resume with ID {resume_id} not found")

            # Verify resume belongs to user (convert both to strings for comparison)
            if resume.user_id != user_id:
                raise ValueError(
                    f"Resume with ID {resume_id} does not belong to user {user_id}"
                )

        return resume, profile, portfolio

    async def generate_resume(
        self,
        user_id: Union[str, PydanticObjectId],
        title: Optional[str] = None,
        company_name: Optional[str] = None,
        job_title: Optional[str] = None,
        job_description: Optional[str] = None,
        profile_id: Optional[Union[str, PydanticObjectId]] = None,
        portfolio_id: Optional[Union[str, PydanticObjectId]] = None,
        template_id: Optional[str] = None,
        resume_id: Optional[Union[str, PydanticObjectId]] = None,
    ) -> Resume:
        """
        Generate a new resume or update an existing one.

        Args:
            user_id: User ID
            title: Resume title (optional)
            company_name: Company name (optional)
            job_title: Job title (optional)
            job_description: Job description (optional)
            profile_id: Profile ID (optional)
            portfolio_id: Portfolio ID (optional)
            template_id: Template ID (optional)
            resume_id: Existing resume ID to update (optional)

        Returns:
            Resume: Generated resume
        """
        # Convert string IDs to PydanticObjectId if needed
        if isinstance(user_id, str):
            user_id = PydanticObjectId(user_id)
        if profile_id and isinstance(profile_id, str):
            profile_id = PydanticObjectId(profile_id)
        if portfolio_id and isinstance(portfolio_id, str):
            portfolio_id = PydanticObjectId(portfolio_id)
        if resume_id and isinstance(resume_id, str):
            resume_id = PydanticObjectId(resume_id)

        # If resume_id is provided, update existing resume
        if resume_id:
            resume = await self.resume_repository.get_by_id(resume_id)
            if resume and resume.user_id == user_id:
                # Update fields if provided
                if title:
                    resume.title = title
                if company_name:
                    resume.company_name = company_name
                if job_title:
                    resume.job_title = job_title
                if job_description:
                    resume.job_description = job_description
                if template_id:
                    resume.template_id = template_id
                if profile_id:
                    resume.profile_id = profile_id
                if portfolio_id:
                    resume.portfolio_id = portfolio_id

                resume.updated_at = datetime.now(timezone.utc)
                await self.resume_repository.update(resume)
                return resume
            else:
                self.logger.warning(
                    f"Resume {resume_id} not found or doesn't belong to user {user_id}"
                )

        # If no existing resume, or it wasn't found, create a new one
        # Find the default profile if not specified
        if not profile_id:
            user = await self.profile_repository.get_by_id(user_id)
            if user and hasattr(user, "default_profile_id") and user.default_profile_id:
                profile_id = user.default_profile_id
            else:
                # Try to get any profile for this user
                profiles = await self.profile_repository.get_by_user_id(user_id)
                if profiles:
                    profile_id = profiles[0].id

        if not profile_id:
            self.logger.error(f"No profile found for user {user_id}")
            raise ValueError("No profile found for user")

        # Create new resume
        resume = Resume(
            user_id=user_id,
            profile_id=profile_id,
            portfolio_id=portfolio_id,
            title=title or "My Resume",
            company_name=company_name,
            job_title=job_title,
            job_description=job_description or "",
            template_id=template_id or "default",
        )

        # Save resume
        await self.resume_repository.create(resume)
        self.logger.info(f"Created new resume: {resume.id}")

        return resume

    async def generate_cover_letter(
        self,
        user_id: Union[str, PydanticObjectId],
        job_description: str,
        title: Optional[str] = None,
        company_name: Optional[str] = None,
        job_title: Optional[str] = None,
        profile_id: Optional[Union[str, PydanticObjectId]] = None,
        portfolio_id: Optional[Union[str, PydanticObjectId]] = None,
        template_id: Optional[str] = None,
        resume_id: Optional[Union[str, PydanticObjectId]] = None,
    ) -> CoverLetter:
        """
        Generate a new cover letter or update an existing one.

        Args:
            user_id: User ID
            job_description: Job description
            title: Cover letter title (optional)
            company_name: Company name (optional)
            job_title: Job title (optional)
            profile_id: Profile ID (optional)
            portfolio_id: Portfolio ID (optional)
            template_id: Template ID (optional)
            resume_id: Existing resume ID to reference or update (optional)

        Returns:
            CoverLetter: Generated cover letter
        """
        # Convert string IDs to PydanticObjectId if needed
        if isinstance(user_id, str):
            user_id = PydanticObjectId(user_id)
        if profile_id and isinstance(profile_id, str):
            profile_id = PydanticObjectId(profile_id)
        if portfolio_id and isinstance(portfolio_id, str):
            portfolio_id = PydanticObjectId(portfolio_id)
        if resume_id and isinstance(resume_id, str):
            resume_id = PydanticObjectId(resume_id)

        # Find the default profile if not specified
        if not profile_id:
            user = await self.profile_repository.get_by_id(user_id)
            if user and hasattr(user, "default_profile_id") and user.default_profile_id:
                profile_id = user.default_profile_id
            else:
                # Try to get any profile for this user
                profiles = await self.profile_repository.get_by_user_id(user_id)
                if profiles:
                    profile_id = profiles[0].id

        if not profile_id:
            self.logger.error(f"No profile found for user {user_id}")
            raise ValueError("No profile found for user")

        # If resume_id is provided, get resume content
        resume_content = {}
        if resume_id:
            resume = await self.resume_repository.get_by_id(resume_id)
            if resume and resume.user_id == user_id:
                resume_content = resume.content or {}
            else:
                self.logger.warning(
                    f"Resume {resume_id} not found or doesn't belong to user {user_id}"
                )
                resume_id = None  # Reset resume_id if it's invalid

        # Create new cover letter
        cover_letter = CoverLetter(
            user_id=user_id,
            profile_id=profile_id,
            portfolio_id=portfolio_id,
            resume_id=resume_id,  # Link to the resume if provided
            title=title
            or f"Cover Letter for {company_name if company_name else 'Job Application'}",
            company_name=company_name,
            job_title=job_title,
            job_description=job_description,
            template_id=template_id or "default",
            content=resume_content,  # Use the resume content if available
        )

        # Save cover letter
        await self.cover_letter_repository.create(cover_letter)
        self.logger.info(f"Created new cover letter: {cover_letter.id}")

        # Generate content
        await self.generate_cover_letter_content(cover_letter.id)

        # Get updated cover letter
        updated_cover_letter = await self.cover_letter_repository.get_by_id(
            cover_letter.id
        )
        return updated_cover_letter

    async def generate_pdf(
        self,
        resume_id: Union[str, PydanticObjectId],
        user_id: Union[str, PydanticObjectId],
        regenerate: bool = False,
    ) -> bytes:
        """
        Generate a PDF for a resume or cover letter.

        Args:
            resume_id: Resume or cover letter ID
            user_id: User ID
            regenerate: Whether to regenerate the PDF even if it exists

        Returns:
            bytes: Generated PDF content
        """
        # Convert string IDs to PydanticObjectId if needed
        if isinstance(user_id, str):
            user_id = PydanticObjectId(user_id)
        if isinstance(resume_id, str):
            resume_id = PydanticObjectId(resume_id)

        # Try to get as resume first
        resume = await self.resume_repository.get_by_id(resume_id)
        if resume and resume.user_id == user_id:
            if resume.resume_pdf and not regenerate:
                return resume.resume_pdf

            # Get profile and portfolio
            profile = await self.profile_repository.get_by_id(resume.profile_id)
            portfolio = None
            if resume.portfolio_id:
                portfolio = await self.portfolio_repository.get_by_id(
                    resume.portfolio_id
                )

            # Generate LaTeX
            latex = await self.latex_service.generate_resume_latex(
                resume, profile, portfolio
            )

            # Compile to PDF
            pdf_bytes = await self.latex_service.compile_latex_to_pdf(latex)

            # Update resume
            resume.resume_pdf = pdf_bytes
            resume.updated_at = datetime.now(timezone.utc)
            await self.resume_repository.update(resume)

            return pdf_bytes

        # Try as cover letter
        cover_letter = await self.cover_letter_repository.get_by_id(resume_id)
        if cover_letter and cover_letter.user_id == user_id:
            if cover_letter.cover_letter_pdf and not regenerate:
                return cover_letter.cover_letter_pdf

            # Get profile and portfolio
            profile = await self.profile_repository.get_by_id(cover_letter.profile_id)
            portfolio = None
            if cover_letter.portfolio_id:
                portfolio = await self.portfolio_repository.get_by_id(
                    cover_letter.portfolio_id
                )

            # Generate LaTeX
            latex = await self.latex_service.generate_cover_letter_latex(
                cover_letter, profile
            )

            # Compile to PDF
            pdf_bytes = await self.latex_service.compile_latex_to_pdf(latex)

            # Update cover letter
            cover_letter.cover_letter_pdf = pdf_bytes
            cover_letter.updated_at = datetime.now(timezone.utc)
            await self.cover_letter_repository.update(cover_letter)

            return pdf_bytes

        # Not found or doesn't belong to user
        self.logger.error(
            f"Document {resume_id} not found or doesn't belong to user {user_id}"
        )
        raise ValueError("Document not found or doesn't belong to user")

    async def generate_resume_content(
        self,
        resume_id: Union[str, PydanticObjectId],
        regenerate_sections: Optional[Dict[str, bool]] = None,
    ) -> Dict[str, Any]:
        """
        Generate content for a resume.

        Args:
            resume_id: Resume ID
            regenerate_sections: Sections to regenerate (dict of section_name: bool)

        Returns:
            Dict[str, Any]: Generated content
        """
        # Convert string ID to PydanticObjectId if needed
        if isinstance(resume_id, str):
            resume_id = PydanticObjectId(resume_id)

        # Get resume
        resume = await self.resume_repository.get_by_id(resume_id)
        if not resume:
            self.logger.error(f"Resume {resume_id} not found")
            raise ValueError("Resume not found")

        # Configure LLM for user
        await self.llm_service.configure_for_user(resume.user_id)

        # Get profile and portfolio
        profile = await self.profile_repository.get_by_id(resume.profile_id)
        if not profile:
            self.logger.error(f"Profile {resume.profile_id} not found")
            raise ValueError("Profile not found")

        portfolio = None
        if resume.portfolio_id:
            portfolio = await self.portfolio_repository.get_by_id(resume.portfolio_id)
            if not portfolio:
                self.logger.warning(f"Portfolio {resume.portfolio_id} not found")

        # Determine which sections to regenerate
        sections_to_process = [
            "personal_information",
            "career_summary",
            "skills",
            "work_experience",
            "education",
            "projects",
            "awards",
            "publications",
            "certifications",
        ]

        if regenerate_sections:
            sections_to_process = [
                s for s in sections_to_process if regenerate_sections.get(s, False)
            ]

        # Initialize content dictionary if it doesn't exist
        if not resume.content:
            resume.content = {}

        # Process each section
        for section_name in sections_to_process:
            try:
                # Get section data from portfolio
                section_data = None

                if section_name == "personal_information":
                    section_data = profile
                elif section_name == "career_summary":
                    section_data = portfolio.career_summary if portfolio else ""
                elif section_name == "skills":
                    section_data = portfolio.skills if portfolio else []
                elif section_name == "work_experience":
                    section_data = portfolio.work_experience if portfolio else []
                elif section_name == "education":
                    section_data = portfolio.education if portfolio else []
                elif section_name == "projects":
                    section_data = portfolio.projects if portfolio else []
                elif section_name == "awards":
                    section_data = portfolio.awards if portfolio else []
                elif section_name == "publications":
                    section_data = portfolio.publications if portfolio else []
                elif section_name == "certifications":
                    section_data = portfolio.certifications if portfolio else []

                # Generate content for section
                if section_name == "personal_information" and profile:
                    resume.content[section_name] = {
                        "name": profile.name,
                        "email": profile.email,
                        "phone": profile.phone,
                        "location": profile.location,
                        "linkedin": profile.linkedin,
                        "github": profile.github,
                        "website": profile.website,
                    }
                elif section_data:
                    if section_name == "career_summary":
                        # Career summary is just a string
                        resume.content[section_name] = section_data
                    else:
                        # Other sections are lists
                        resume.content[section_name] = section_data

            except Exception as e:
                self.logger.error(
                    f"Error generating content for section {section_name}: {e}"
                )
                # Continue with other sections even if one fails

        # Update resume
        resume.updated_at = datetime.now(timezone.utc)
        await self.resume_repository.update(resume)

        return resume.content

    async def generate_cover_letter_content(
        self,
        cover_letter_id: Union[str, PydanticObjectId],
        regenerate: bool = False,
    ) -> str:
        """
        Generate content for a cover letter.

        Args:
            cover_letter_id: Cover letter ID
            regenerate: Whether to regenerate even if content already exists

        Returns:
            str: Generated cover letter content
        """
        # Convert string ID to PydanticObjectId if needed
        if isinstance(cover_letter_id, str):
            cover_letter_id = PydanticObjectId(cover_letter_id)

        # Get cover letter
        cover_letter = await self.cover_letter_repository.get_by_id(cover_letter_id)
        if not cover_letter:
            self.logger.error(f"Cover letter {cover_letter_id} not found")
            raise ValueError("Cover letter not found")

        # If cover letter content exists and regenerate is False, return existing
        if cover_letter.cover_letter_content and not regenerate:
            return cover_letter.cover_letter_content

        # Configure LLM for user
        await self.llm_service.configure_for_user(str(cover_letter.user_id))

        # Get profile and portfolio
        profile = await self.profile_repository.get_by_id(cover_letter.profile_id)
        if not profile:
            self.logger.error(f"Profile {cover_letter.profile_id} not found")
            raise ValueError("Profile not found")

        portfolio = None
        if cover_letter.portfolio_id:
            portfolio = await self.portfolio_repository.get_by_id(
                cover_letter.portfolio_id
            )
            if not portfolio:
                self.logger.warning(f"Portfolio {cover_letter.portfolio_id} not found")

        # Get resume content from cover letter or build basic content
        resume_content = cover_letter.content
        if not resume_content:
            # Build basic content
            resume_content = {
                "personal_information": {
                    "name": profile.full_name,
                    "email": profile.email,
                    "phone": profile.phone,
                    "address": profile.address,
                    "linkedin": profile.linkedin,
                    "github": profile.github,
                    "website": profile.website,
                },
                "career_summary": portfolio.career_summary if portfolio else "",
                "skills": portfolio.skills if portfolio else [],
                "work_experience": portfolio.work_experience if portfolio else [],
                "education": portfolio.education if portfolio else [],
                "projects": portfolio.projects if portfolio else [],
            }

        # Generate cover letter
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
