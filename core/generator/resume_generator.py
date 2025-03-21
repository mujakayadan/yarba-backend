"""Resume generator for creating resumes from user data."""

import json
from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from core.latex.compilers import ResumeCompiler
from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.models.resume import Resume
from core.repositories.preamble_repository import PreambleRepository
from core.repositories.tex_header_repository import TexHeaderRepository
from core.repositories.tex_template_repository import TexTemplateRepository
from core.services.llm_service import LLMService

from .base import BaseGenerator
from .utils.prompt_builder import build_resume_prompt

logger = get_logger(__name__)


class ResumeGenerator(BaseGenerator):
    """Generator for creating resumes from user data."""

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
        """Initialize the resume generator.

        Args:
            profile: User profile
            resume: Resume to generate
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
        self.logger = self.logger.getChild("ResumeGenerator")

    async def generate(self, **kwargs) -> Dict[str, Any]:
        """Generate resume content.

        Args:
            **kwargs: Additional arguments for generation

        Returns:
            Dict[str, Any]: Generated resume content with both JSON data and LaTeX
        """
        self.logger.info(f"Generating resume for user: {self.profile.user_id}")

        result = {
            "resume_id": str(self.resume.id),
            "user_id": str(self.profile.user_id),
            "json_content": {},
            "latex_content": "",
        }

        # Sections to process
        sections = [
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
        for section_name in sections:
            section_content = await self._generate_section(section_name)
            if section_content:
                result["json_content"][section_name] = section_content

        # Generate LaTeX content
        result["latex_content"] = await self._generate_latex(result["json_content"])

        return result

    async def _generate_section(self, section_name: str) -> Optional[Any]:
        """Generate content for a specific section.

        Args:
            section_name: Name of the section to generate

        Returns:
            Optional[Any]: Generated section content, or None if generation failed
        """
        try:
            # Check if section should be processed or hardcoded
            processing_preference = await self._get_section_processing_preference(
                section_name
            )

            # Get section data from portfolio based on section name
            section_data = self._get_section_data(section_name)

            # If no data or section should be hardcoded, return data as is
            if not section_data or processing_preference.lower() == "hardcode":
                return section_data

            # Process with LLM service
            if not self.llm_service:
                self.logger.warning(
                    "LLM service not available, returning hardcoded data"
                )
                return section_data

            # Configure LLM service for this user if needed
            await self.llm_service.configure_for_user(str(self.profile.user_id))

            # Create context for LLM
            context = {
                "section_data": section_data,
                "job_title": self.resume.job_title,
                "company_name": self.resume.company_name,
            }

            # Generate content with LLM
            generated_content = await self.llm_service.generate_section(
                section_name=section_name,
                context=context,
                job_description=self.resume.job_description or "",
            )

            # Try to parse JSON response if possible
            try:
                return json.loads(generated_content)
            except json.JSONDecodeError:
                # If not valid JSON, return as string
                return generated_content

        except Exception as e:
            self.logger.error(f"Error generating section {section_name}: {e}")
            return None

    def _get_section_data(self, section_name: str) -> Any:
        """Get section data from portfolio.

        Args:
            section_name: Name of the section

        Returns:
            Any: Section data
        """
        if not self.portfolio:
            return None

        if section_name == "personal_information":
            return {
                "full_name": self.profile.full_name,
                "email": self.profile.email,
                "phone": self.profile.phone,
                "address": self.profile.address,
                "linkedin": self.profile.linkedin,
                "github": self.profile.github,
                "website": self.profile.website,
            }
        elif section_name == "career_summary":
            return self.portfolio.career_summary
        elif section_name == "skills":
            return self.portfolio.skills
        elif section_name == "work_experience":
            return self.portfolio.work_experience
        elif section_name == "education":
            return self.portfolio.education
        elif section_name == "projects":
            return self.portfolio.projects
        elif section_name == "awards":
            return self.portfolio.awards
        elif section_name == "publications":
            return self.portfolio.publications

        return None

    async def _generate_latex(self, content: Dict[str, Any]) -> str:
        """Generate LaTeX content from resume data.

        Args:
            content: Resume content in JSON format

        Returns:
            str: Generated LaTeX content
        """
        try:
            # Get resume preamble
            preamble = await self._get_preamble("resume_preamble")
            if not preamble:
                self.logger.warning("Resume preamble not found")
                preamble = self._get_default_preamble()

            # Build document structure
            latex = f"{preamble}\n\n\\begin{{document}}\n\n"

            # Add personal information section
            personal_info = content.get("personal_information", {})
            if personal_info:
                header = await self._get_tex_header("personal_information")
                if header:
                    latex += self._apply_header_template(header, personal_info)

            # Add each section in order
            section_order = [
                "career_summary",
                "skills",
                "work_experience",
                "education",
                "projects",
                "awards",
                "publications",
            ]

            for section_name in section_order:
                section_content = content.get(section_name)
                if not section_content:
                    continue

                header = await self._get_tex_header(section_name)
                if header:
                    latex += self._apply_header_template(header, section_content)
                else:
                    # Fallback to generic section formatting
                    latex += f"\\section{{{section_name.replace('_', ' ').title()}}}\n"
                    latex += f"{json.dumps(section_content, indent=2)}\n\n"

            # Close document
            latex += "\\end{document}"

            return latex

        except Exception as e:
            self.logger.error(f"Error generating LaTeX: {e}")
            return f"% Error generating LaTeX: {e}"

    def _apply_header_template(self, template: str, data: Any) -> str:
        """Apply data to a LaTeX template.

        Args:
            template: LaTeX template string
            data: Data to apply to the template

        Returns:
            str: Rendered LaTeX content
        """
        # Simple template replacement - in a real implementation, this would
        # be more sophisticated with proper template rendering
        result = template

        if isinstance(data, dict):
            for key, value in data.items():
                result = result.replace(f"{{{{ {key} }}}}", str(value))

        return result

    def _get_default_preamble(self) -> str:
        """Get a default LaTeX preamble.

        Returns:
            str: Default LaTeX preamble
        """
        return """\\documentclass[11pt,a4paper]{article}
\\usepackage[margin=1in]{geometry}
\\usepackage{fontspec}
\\usepackage{enumitem}
\\setmainfont{Arial}
\\pagestyle{empty}
"""

    async def _generate_pdf(self) -> Optional[bytes]:
        """Generate PDF from resume content.

        Returns:
            Optional[bytes]: Generated PDF content
        """
        try:
            compiler = ResumeCompiler()
            pdf_content = await compiler.generate_pdf(self.resume)
            if pdf_content:
                self.resume.resume_pdf = pdf_content
                return pdf_content
        except Exception as e:
            self.logger.error(f"Error generating PDF: {str(e)}")

        return None
