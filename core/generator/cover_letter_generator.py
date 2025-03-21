"""Cover letter generator for creating cover letters from user data."""

import json
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from core.latex.compilers import CoverLetterCompiler
from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.models.resume import Resume
from core.repositories.preamble_repository import PreambleRepository
from core.repositories.tex_header_repository import TexHeaderRepository
from core.repositories.tex_template_repository import TexTemplateRepository
from core.services.llm_service import LLMService

from .base import BaseGenerator
from .utils.prompt_builder import build_cover_letter_prompt

logger = get_logger(__name__)


class CoverLetterGenerator(BaseGenerator):
    """Generator for creating cover letters from user data."""

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
        """Initialize the cover letter generator.

        Args:
            profile: User profile
            resume: Resume to generate cover letter for
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
        self.logger = self.logger.getChild("CoverLetterGenerator")

    async def generate(self, **kwargs) -> Dict[str, Any]:
        """Generate cover letter content.

        Args:
            **kwargs: Additional arguments for generation
                - recipient_name: Name of the recipient
                - recipient_title: Title of the recipient
                - recipient_company: Company of the recipient
                - recipient_address: Address of the recipient
                - salutation: Salutation to use

        Returns:
            Dict[str, Any]: Generated cover letter content with both JSON data and LaTeX
        """
        self.logger.info(f"Generating cover letter for user: {self.profile.user_id}")

        result = {
            "resume_id": str(self.resume.id),
            "user_id": str(self.profile.user_id),
            "json_content": {},
            "latex_content": "",
        }

        # Generate cover letter content
        content = await self._generate_cover_letter(**kwargs)
        if content:
            result["json_content"] = content

        # Generate LaTeX content
        result["latex_content"] = await self._generate_latex(result["json_content"])

        return result

    async def _generate_cover_letter(self, **kwargs) -> Dict[str, Any]:
        """Generate the cover letter content.

        Args:
            **kwargs: Additional arguments for generation

        Returns:
            Dict[str, Any]: Generated cover letter content
        """
        try:
            # Initialize content with recipient information
            content = {
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
                        self.resume.company_name or "",
                    ),
                    "address": kwargs.get("recipient_address", ""),
                },
                "salutation": kwargs.get("salutation", "Dear Hiring Manager"),
                "closing": kwargs.get("closing", "Sincerely"),
            }

            # Process with LLM service if available
            if self.llm_service:
                try:
                    # Configure LLM service for this user if needed
                    await self.llm_service.configure_for_user(str(self.profile.user_id))

                    # Generate cover letter body with LLM
                    generated_content = await self.llm_service.generate_cover_letter(
                        resume_content=self.resume.content or {},
                        job_description=self.resume.job_description or "",
                        company_name=self.resume.company_name or "",
                        job_title=self.resume.job_title or "",
                    )

                    # Try to parse JSON response if possible
                    try:
                        letter_body = json.loads(generated_content)
                        # Update content with generated body
                        if isinstance(letter_body, dict):
                            if "salutation" in letter_body:
                                content["salutation"] = letter_body["salutation"]
                            if "content" in letter_body:
                                content["content"] = letter_body["content"]
                            if "closing" in letter_body:
                                content["closing"] = letter_body["closing"]
                        else:
                            content["content"] = generated_content
                    except json.JSONDecodeError:
                        # If not valid JSON, use as plain text content
                        content["content"] = generated_content

                except Exception as e:
                    self.logger.error(f"Error generating cover letter with LLM: {e}")
                    # Fallback to default content
                    content["content"] = self._get_default_content()
            else:
                # Fallback to default content if LLM not available
                self.logger.warning("LLM service not available, using default content")
                content["content"] = self._get_default_content()

            return content

        except Exception as e:
            self.logger.error(f"Error generating cover letter: {e}")
            return {
                "personal_info": {
                    "full_name": self.profile.full_name,
                    "email": self.profile.email,
                },
                "content": f"Error generating cover letter: {e}",
            }

    def _get_default_content(self) -> str:
        """Get default cover letter content when LLM is unavailable.

        Returns:
            str: Default cover letter content
        """
        job_title = self.resume.job_title or "the open position"
        company_name = self.resume.company_name or "your company"

        return (
            f"I am writing to express my interest in the {job_title} position at {company_name}. "
            "With my background and experience, I believe I would be a valuable addition to your team.\n\n"
            "Throughout my career, I have developed strong skills that align well with the requirements "
            "of this position. My experience has prepared me to excel in this role.\n\n"
            f"I am excited about the opportunity to bring my skills and experiences to {company_name} "
            "and help drive your continued success. Thank you for considering my application."
        )

    async def _generate_latex(self, content: Dict[str, Any]) -> str:
        """Generate LaTeX content from cover letter data.

        Args:
            content: Cover letter content in JSON format

        Returns:
            str: Generated LaTeX content
        """
        try:
            # Get cover letter preamble
            preamble = await self._get_preamble("cover_letter_preamble")
            if not preamble:
                self.logger.warning("Cover letter preamble not found")
                preamble = self._get_default_preamble()

            # Build document structure
            latex = f"{preamble}\n\n\\begin{{document}}\n\n"

            # Add personal information section
            personal_info = content.get("personal_info", {})
            if personal_info:
                header = await self._get_tex_header("cover_letter_header")
                if header:
                    latex += self._apply_header_template(header, personal_info)
                else:
                    # Fallback formatting
                    latex += f"\\begin{{flushright}}\n"
                    latex += f"{personal_info.get('full_name', '')}\\\\\n"
                    if personal_info.get("address"):
                        latex += f"{personal_info.get('address', '')}\\\\\n"
                    if personal_info.get("phone"):
                        latex += f"{personal_info.get('phone', '')}\\\\\n"
                    latex += f"{personal_info.get('email', '')}\n"
                    latex += f"\\end{{flushright}}\n\n"

            # Add date
            latex += "\\today\n\n"

            # Add recipient information
            recipient_info = content.get("recipient_info", {})
            if recipient_info:
                latex += f"{recipient_info.get('name', '')}\\\\\n"
                if recipient_info.get("title"):
                    latex += f"{recipient_info.get('title', '')}\\\\\n"
                if recipient_info.get("company"):
                    latex += f"{recipient_info.get('company', '')}\\\\\n"
                if recipient_info.get("address"):
                    latex += f"{recipient_info.get('address', '')}\\\\\n"
                latex += "\n"

            # Add salutation
            latex += f"{content.get('salutation', 'Dear Hiring Manager')},\n\n"

            # Add content
            letter_content = content.get("content", "")
            # Format paragraphs for LaTeX
            if letter_content:
                paragraphs = letter_content.split("\n\n")
                for paragraph in paragraphs:
                    latex += f"{paragraph}\n\n"

            # Add closing
            latex += f"\n{content.get('closing', 'Sincerely')},\\\\\\\\\n"
            latex += f"{personal_info.get('full_name', '')}\n"

            # Close document
            latex += "\\end{document}"

            return latex

        except Exception as e:
            self.logger.error(f"Error generating LaTeX: {e}")
            return f"% Error generating LaTeX: {e}"

    def _apply_header_template(self, template: str, data: Dict[str, Any]) -> str:
        """Apply data to a LaTeX template.

        Args:
            template: LaTeX template string
            data: Data to apply to the template

        Returns:
            str: Rendered LaTeX content
        """
        # Simple template replacement
        result = template

        for key, value in data.items():
            result = result.replace(f"{{{{ {key} }}}}", str(value) if value else "")

        return result

    def _get_default_preamble(self) -> str:
        """Get a default LaTeX preamble for cover letters.

        Returns:
            str: Default LaTeX preamble
        """
        return """\\documentclass[11pt,a4paper]{letter}
\\usepackage[margin=1in]{geometry}
\\usepackage{fontspec}
\\usepackage{enumitem}
\\setmainfont{Arial}
\\pagestyle{empty}
"""

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
