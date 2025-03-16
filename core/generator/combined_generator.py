"""Combined generator implementation."""

from typing import Any, Dict, Optional, Tuple

from config.logging_config import get_logger
from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.models.resume import Resume

from .base import BaseGenerator
from .cover_letter_generator import CoverLetterGenerator
from .resume_generator import ResumeGenerator

logger = get_logger(__name__)


class CombinedGenerator(BaseGenerator):
    """Combined generator for creating both resume and cover letter."""

    async def generate(self, **kwargs) -> Dict[str, Any]:
        """Generate both resume and cover letter content.

        Args:
            **kwargs: Additional arguments for generation
                - generate_pdf: Whether to generate PDFs (default: False)
                - resume_kwargs: Additional arguments for resume generation
                - cover_letter_kwargs: Additional arguments for cover letter generation

        Returns:
            Dict[str, Any]: Generated content with both resume and cover letter
        """
        if not self.profile or not self.resume:
            raise ValueError("Profile and Resume are required for generation")

        # Preprocess data
        data = await self.preprocess(**kwargs)

        # Initialize generators
        resume_generator = ResumeGenerator(
            profile=self.profile,
            portfolio=self.portfolio,
            resume=self.resume,
            settings=self.settings,
        )

        cover_letter_generator = CoverLetterGenerator(
            profile=self.profile,
            portfolio=self.portfolio,
            resume=self.resume,
            settings=self.settings,
        )

        # Generate resume content
        resume_kwargs = kwargs.get("resume_kwargs", {})
        resume_kwargs["generate_pdf"] = kwargs.get("generate_pdf", False)
        resume_content = await resume_generator.generate(**resume_kwargs)

        # Generate cover letter content
        cover_letter_kwargs = kwargs.get("cover_letter_kwargs", {})
        cover_letter_kwargs["generate_pdf"] = kwargs.get("generate_pdf", False)
        cover_letter_content = await cover_letter_generator.generate(
            **cover_letter_kwargs
        )

        # Combine content
        combined_content = {
            "resume": resume_content,
            "cover_letter": cover_letter_content,
        }

        # Postprocess content
        processed_content = await self.postprocess(combined_content, **kwargs)

        return processed_content

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
