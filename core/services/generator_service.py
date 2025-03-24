"""Service for document generation using DocumentGenerator."""

import os
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

from beanie import PydanticObjectId
from fastapi import HTTPException

from config.logging_config import get_logger
from config.settings import Settings
from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.models.resume import Resume
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
        llm_service: LLMService,
        latex_service: LatexService,
    ):
        """
        Initialize the document generator service.

        Args:
            resume_repository: Repository for accessing resume data
            profile_repository: Repository for accessing profile data
            portfolio_repository: Repository for accessing portfolio data
            llm_service: Service for LLM operations
            latex_service: Service for LaTeX operations
        """
        self.resume_repository = resume_repository
        self.profile_repository = profile_repository
        self.portfolio_repository = portfolio_repository
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
            if str(resume.user_id) != str(user_id):
                raise ValueError(
                    f"Resume with ID {resume_id} does not belong to user {user_id}"
                )

        return resume, profile, portfolio

    async def generate_resume(
        self,
        user_id: PydanticObjectId,
        job_description: str,
        selected_sections: Dict[str, str],
        resume_id: Optional[PydanticObjectId] = None,
    ) -> Resume:
        """
        Generate a resume.

        Args:
            user_id: User ID
            job_description: Job description
            selected_sections: Dictionary of section names and generation method
            resume_id: Optional existing resume ID to update

        Returns:
            Generated resume
        """
        try:
            # Configure LLM for user
            await self.llm_service.configure_for_user(user_id)

            # Get user data
            resume, profile, portfolio = await self._get_user_data(
                user_id=user_id, resume_id=resume_id
            )

            # If resume doesn't exist, create it
            if not resume:
                resume = await self.resume_repository.create(
                    user_id=user_id,
                    profile_id=str(profile.id),
                    portfolio_id=str(portfolio.id),
                    job_description=job_description,
                    content={},
                    is_cover_letter=False,
                )
            else:
                # Update job description
                resume.job_description = job_description
                resume = await self.resume_repository.update(
                    id=str(resume.id),
                    update_data={"job_description": job_description},
                )

            # Process each selected section
            content = resume.content or {}
            for section_name, generation_method in selected_sections.items():
                # Get section data from portfolio
                section_data = None
                if section_name == "personal_information":
                    section_data = profile
                elif section_name == "skills":
                    section_data = await self.portfolio_repository.get_skills(user_id)
                elif section_name == "work_experience":
                    section_data = await self.portfolio_repository.get_work_experience(
                        user_id
                    )
                elif section_name == "education":
                    section_data = await self.portfolio_repository.get_education(
                        user_id
                    )
                elif section_name == "projects":
                    section_data = await self.portfolio_repository.get_projects(user_id)

                # If no data or not selected for generation, skip
                if section_data is None:
                    self.logger.warning(f"No data for section {section_name}")
                    continue

                # Generate content based on method
                is_ai_generation = generation_method.lower() == "ai"

                if is_ai_generation:
                    # Use LLM to generate content
                    context = {
                        "section_data": section_data,
                        "job_title": resume.job_title or "",
                        "company_name": resume.company_name or "",
                    }

                    content[section_name] = await self.llm_service.generate_section(
                        section_name=section_name,
                        context=context,
                        job_description=job_description,
                    )
                else:
                    # Use raw data
                    content[section_name] = section_data

            # Update resume content
            resume = await self.resume_repository.update(
                id=str(resume.id),
                update_data={"content": content},
            )

            return resume

        except Exception as e:
            self.logger.error(f"Error generating resume: {str(e)}")
            raise

    async def generate_cover_letter(
        self,
        user_id: PydanticObjectId,
        job_description: str,
        title: str,
        template_id: str,
        resume_id: Optional[PydanticObjectId] = None,
    ) -> Resume:
        """
        Generate a cover letter.

        Args:
            user_id: User ID
            job_description: Job description
            title: Cover letter title
            template_id: Template ID
            resume_id: Optional existing cover letter ID to update

        Returns:
            Generated cover letter
        """
        try:
            # Configure LLM for user
            await self.llm_service.configure_for_user(user_id)

            # Get user data
            resume, profile, portfolio = await self._get_user_data(
                user_id=user_id, resume_id=resume_id
            )

            # If resume doesn't exist, create it
            if not resume:
                resume = await self.resume_repository.create(
                    user_id=user_id,
                    title=title,
                    profile_id=str(profile.id),
                    portfolio_id=str(portfolio.id),
                    template_id=template_id,
                    job_description=job_description,
                    content={},
                    is_cover_letter=True,
                )
            else:
                # Ensure it's a cover letter
                if not resume.is_cover_letter:
                    raise ValueError(
                        f"Resume with ID {resume_id} is not a cover letter"
                    )

                # Update job description
                resume.job_description = job_description
                resume = await self.resume_repository.update(
                    id=str(resume.id),
                    update_data={"job_description": job_description},
                )

            # Generate cover letter content
            cover_letter_content = await self.llm_service.generate_cover_letter(
                profile=profile,
                job_description=job_description,
            )

            # Update resume content
            content = {"cover_letter": cover_letter_content}
            resume = await self.resume_repository.update(
                id=str(resume.id),
                update_data={"content": content},
            )

            return resume

        except Exception as e:
            self.logger.error(f"Error generating cover letter: {str(e)}")
            raise

    async def generate_pdf(
        self,
        resume_id: Union[str, PydanticObjectId],
        user_id: PydanticObjectId,
    ) -> bytes:
        """
        Generate a PDF from a resume or cover letter.

        Args:
            resume_id: Resume or cover letter ID
            user_id: User ID

        Returns:
            PDF content as bytes

        Raises:
            ValueError: If resume or cover letter not found
        """
        try:
            # Get resume
            resume = await self.resume_repository.get_by_id(resume_id)
            if not resume:
                raise ValueError(f"Document with ID {resume_id} not found")

            # Verify ownership
            if str(resume.user_id) != user_id:
                raise ValueError(
                    f"Document with ID {resume_id} does not belong to user {user_id}"
                )

            # Get profile and portfolio
            profile = await self.profile_repository.get_by_id(resume.profile_id)
            if not profile:
                raise ValueError(f"Profile with ID {resume.profile_id} not found")

            portfolio = await self.portfolio_repository.get_by_id(resume.portfolio_id)
            if not portfolio:
                raise ValueError(f"Portfolio with ID {resume.portfolio_id} not found")

            # Generate LaTeX content
            if resume.is_cover_letter:
                latex_content = await self.latex_service.generate_cover_letter_latex(
                    resume=resume,
                    profile=profile,
                    portfolio=portfolio,
                )
            else:
                latex_content = await self.latex_service.generate_resume_latex(
                    resume=resume,
                    profile=profile,
                    portfolio=portfolio,
                )

            # Compile LaTeX to PDF
            pdf_content = await self.latex_service.compile_latex_to_pdf(latex_content)

            # Save PDF to disk if settings specify
            if settings.files.save_generated_pdfs:
                try:
                    # Create directory if it doesn't exist
                    output_dir = Path(settings.files.pdf_output_dir)
                    os.makedirs(output_dir, exist_ok=True)

                    # Determine filename
                    document_type = (
                        "cover_letter" if resume.is_cover_letter else "resume"
                    )
                    filename = f"{document_type}_{resume_id}.pdf"
                    file_path = output_dir / filename

                    # Write PDF to file
                    with open(file_path, "wb") as f:
                        f.write(pdf_content)

                    self.logger.info(f"Saved PDF to {file_path}")
                except Exception as e:
                    self.logger.error(f"Error saving PDF to disk: {str(e)}")
                    # Continue even if saving to disk fails

            return pdf_content

        except Exception as e:
            self.logger.error(f"Error generating PDF: {str(e)}")
            raise
