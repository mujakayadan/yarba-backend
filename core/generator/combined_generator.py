"""Combined generator for creating both resume and cover letter."""

from typing import Any, Dict, Optional

from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.models.resume import Resume
from core.repositories.preamble_repository import PreambleRepository
from core.repositories.tex_header_repository import TexHeaderRepository
from core.repositories.tex_template_repository import TexTemplateRepository
from core.services.llm_service import LLMService

from .base import BaseGenerator
from .cover_letter_generator import CoverLetterGenerator
from .resume_generator import ResumeGenerator


class CombinedGenerator(BaseGenerator):
    """Generator for creating both resume and cover letter."""

    def __init__(
        self,
        profile: Profile,
        resume: Resume,
        portfolio: Optional[Portfolio] = None,
        llm_service: Optional[LLMService] = None,
        preamble_repository: Optional[PreambleRepository] = None,
        tex_header_repository: Optional[TexHeaderRepository] = None,
        tex_template_repository: Optional[TexTemplateRepository] = None,
    ):
        """Initialize the combined generator.

        Args:
            profile: User profile
            resume: Resume to generate content for
            portfolio: Optional portfolio data
            llm_service: LLM service for content generation
            preamble_repository: Repository for LaTeX preambles
            tex_header_repository: Repository for LaTeX headers
            tex_template_repository: Repository for LaTeX templates
        """
        super().__init__(
            profile=profile,
            resume=resume,
            portfolio=portfolio,
            llm_service=llm_service,
            preamble_repository=preamble_repository,
            tex_header_repository=tex_header_repository,
            tex_template_repository=tex_template_repository,
        )
        self.logger = self.logger.getChild("CombinedGenerator")

        # Initialize child generators
        self.resume_generator = ResumeGenerator(
            profile=profile,
            resume=resume,
            portfolio=portfolio,
            llm_service=llm_service,
            preamble_repository=preamble_repository,
            tex_header_repository=tex_header_repository,
            tex_template_repository=tex_template_repository,
        )

        self.cover_letter_generator = CoverLetterGenerator(
            profile=profile,
            resume=resume,
            portfolio=portfolio,
            llm_service=llm_service,
            preamble_repository=preamble_repository,
            tex_header_repository=tex_header_repository,
            tex_template_repository=tex_template_repository,
        )

    async def generate(self, **kwargs) -> Dict[str, Any]:
        """Generate both resume and cover letter content.

        Args:
            **kwargs: Additional arguments for generation
                - resume_kwargs: Arguments to pass to the resume generator
                - cover_letter_kwargs: Arguments to pass to the cover letter generator

        Returns:
            Dict[str, Any]: Generated content for both resume and cover letter
        """
        self.logger.info(
            f"Generating combined content for user: {self.profile.user_id}"
        )

        result = {
            "resume_id": str(self.resume.id),
            "user_id": str(self.profile.user_id),
            "resume": {},
            "cover_letter": {},
        }

        # Extract specific kwargs for each generator
        resume_kwargs = kwargs.get("resume_kwargs", {})
        cover_letter_kwargs = kwargs.get("cover_letter_kwargs", {})

        # Generate resume
        try:
            resume_result = await self.resume_generator.generate(**resume_kwargs)
            result["resume"] = resume_result
            self.logger.info("Resume generation completed")
        except Exception as e:
            self.logger.error(f"Error generating resume: {e}")
            result["resume"] = {"error": str(e)}

        # Generate cover letter
        try:
            # Pass resume content to cover letter generation if needed
            if "json_content" in result.get("resume", {}):
                # Update the resume content before generating cover letter
                self.resume.content = result["resume"]["json_content"]

            cover_letter_result = await self.cover_letter_generator.generate(
                **cover_letter_kwargs
            )
            result["cover_letter"] = cover_letter_result
            self.logger.info("Cover letter generation completed")
        except Exception as e:
            self.logger.error(f"Error generating cover letter: {e}")
            result["cover_letter"] = {"error": str(e)}

        # Set all content in resume for persistence
        try:
            if "json_content" in result.get("resume", {}):
                self.resume.content = result["resume"]["json_content"]

            if "latex_content" in result.get("resume", {}):
                self.resume.resume_latex = result["resume"]["latex_content"]

            if "json_content" in result.get("cover_letter", {}):
                self.resume.cover_letter_content = result["cover_letter"][
                    "json_content"
                ]

            if "latex_content" in result.get("cover_letter", {}):
                self.resume.cover_letter_latex = result["cover_letter"]["latex_content"]

        except Exception as e:
            self.logger.error(f"Error updating resume with generated content: {e}")

        return result

    async def preprocess(self, **kwargs) -> Dict[str, Any]:
        """Preprocess data before generation.

        Args:
            **kwargs: Additional arguments for preprocessing

        Returns:
            Dict[str, Any]: Preprocessed data
        """
        # Add job targeting information if not already present
        if self.resume:
            if not self.resume.job_title and "job_title" in kwargs:
                self.resume.job_title = kwargs["job_title"]

            if not self.resume.company_name and "company_name" in kwargs:
                self.resume.company_name = kwargs["company_name"]

            if not self.resume.job_description and "job_description" in kwargs:
                self.resume.job_description = kwargs["job_description"]

        return await super().preprocess(**kwargs)

    async def postprocess(self, content: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Postprocess generated content.

        Args:
            content: Generated content
            **kwargs: Additional arguments for postprocessing

        Returns:
            Dict[str, Any]: Postprocessed content
        """
        # Add metadata
        content["metadata"] = {
            "job_title": self.resume.job_title,
            "company_name": self.resume.company_name,
            "generated_at": self.resume.updated_at.isoformat(),
        }

        return await super().postprocess(content, **kwargs)
