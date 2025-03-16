"""Cover letter generator implementation."""

from typing import Any, Dict, Optional

from config.logging_config import get_logger
from core.latex.compilers import CoverLetterCompiler
from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.models.resume import Resume

from .base import BaseGenerator
from .utils.prompt_builder import build_cover_letter_prompt

logger = get_logger(__name__)


class CoverLetterGenerator(BaseGenerator):
    """Cover letter generator implementation."""

    async def generate(self, **kwargs) -> Dict[str, Any]:
        """Generate cover letter content.

        Args:
            **kwargs: Additional arguments for generation
                - job_description: Job description to tailor the cover letter to
                - company_name: Company name to include in the cover letter
                - job_title: Job title to include in the cover letter
                - recipient_name: Name of the recipient
                - recipient_title: Title of the recipient
                - recipient_company: Company of the recipient
                - recipient_address: Address of the recipient
                - recipient_email: Email of the recipient
                - recipient_phone: Phone of the recipient
                - salutation: Salutation to use (default: "Dear Hiring Manager")
                - closing: Closing to use (default: "Sincerely")
                - paragraphs: Number of paragraphs to generate (default: 3)
                - generate_pdf: Whether to generate a PDF (default: False)

        Returns:
            Dict[str, Any]: Generated cover letter content
        """
        if not self.profile or not self.resume:
            raise ValueError("Profile and Resume are required for generation")

        # Preprocess data
        data = await self.preprocess(**kwargs)

        # Get model settings
        model_settings = self.get_model_settings()

        # Build prompt for cover letter
        prompt = build_cover_letter_prompt(
            profile=self.profile,
            portfolio=self.portfolio,
            resume=self.resume,
            job_description=kwargs.get("job_description")
            or self.resume.job_description,
            job_title=kwargs.get("job_title") or self.resume.job_title,
            company_name=kwargs.get("company_name") or self.resume.company_name,
            recipient_name=kwargs.get("recipient_name"),
            recipient_title=kwargs.get("recipient_title"),
            recipient_company=kwargs.get("recipient_company"),
            recipient_address=kwargs.get("recipient_address"),
            paragraphs=kwargs.get("paragraphs", 3),
        )

        # TODO: Implement LLM client call
        # For now, return placeholder content
        self.logger.info("Generating cover letter content")

        # Prepare cover letter content
        cover_letter_content = {
            "personal_info": {
                "full_name": self.profile.full_name,
                "email": self.profile.email,
                "phone": self.profile.phone,
                "address": self.profile.address,
                "linkedin": self.profile.linkedin,
            },
            "recipient_info": {
                "name": kwargs.get("recipient_name", "Hiring Manager"),
                "title": kwargs.get("recipient_title", ""),
                "company": kwargs.get(
                    "recipient_company",
                    kwargs.get("company_name") or self.resume.company_name or "",
                ),
                "address": kwargs.get("recipient_address", ""),
                "email": kwargs.get("recipient_email", ""),
                "phone": kwargs.get("recipient_phone", ""),
            },
            "salutation": kwargs.get("salutation", "Dear Hiring Manager"),
            "content": "I am writing to express my interest in the position of "
            + (kwargs.get("job_title") or self.resume.job_title or "the open position")
            + " at "
            + (kwargs.get("company_name") or self.resume.company_name or "your company")
            + ". With my background in [relevant field] and experience in [relevant skills], I believe I would be a valuable addition to your team.\n\n"
            + "Throughout my career, I have developed strong skills in [key skills] that align well with the requirements of this position. My experience at [previous company] has prepared me to excel in this role by [specific achievement or skill].\n\n"
            + "I am excited about the opportunity to bring my unique skills and experiences to "
            + (kwargs.get("company_name") or self.resume.company_name or "your company")
            + " and help drive your continued success. Thank you for considering my application.",
            "closing": kwargs.get("closing", "Sincerely"),
        }

        # Postprocess content
        processed_content = await self.postprocess(cover_letter_content, **kwargs)

        # Update resume cover letter content
        self.resume.cover_letter_content = processed_content

        # Generate PDF if requested
        if kwargs.get("generate_pdf", False):
            await self._generate_pdf()

        return processed_content

    async def _generate_pdf(self) -> Optional[bytes]:
        """Generate PDF from cover letter content.

        Returns:
            Optional[bytes]: Generated PDF content
        """
        try:
            compiler = CoverLetterCompiler()
            pdf_content = await compiler.generate_pdf(self.resume)
            if pdf_content:
                self.resume.cover_letter_pdf = pdf_content
                return pdf_content
        except Exception as e:
            self.logger.error(f"Error generating PDF: {str(e)}")

        return None
