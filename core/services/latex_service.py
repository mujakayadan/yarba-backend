"""LaTeX service for LaTeX document generation."""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from config.logging_config import get_logger
from config.settings import Settings
from core.exceptions.base import InternalServerException
from core.latex.compilers import CoverLetterCompiler, ResumeCompiler
from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.models.resume import Resume
from core.repositories.preamble_repository import PreambleRepository
from core.repositories.tex_header_repository import TexHeaderRepository
from core.repositories.tex_template_repository import TexTemplateRepository

settings = Settings()
logger = get_logger(__name__)


class LatexService:
    """Service for LaTeX document generation."""

    def __init__(
        self,
        preamble_repository: PreambleRepository,
        header_repository: TexHeaderRepository,
        template_repository: TexTemplateRepository,
    ):
        """
        Initialize LaTeX service.

        Args:
            preamble_repository: Repository for LaTeX preambles
            header_repository: Repository for LaTeX headers
            template_repository: Repository for LaTeX templates
        """
        self.preamble_repository = preamble_repository
        self.header_repository = header_repository
        self.template_repository = template_repository
        self.logger = logger

        # Initialize compilers directly
        self.resume_compiler = ResumeCompiler()
        self.cover_letter_compiler = CoverLetterCompiler()

    async def get_default_preamble(self) -> str:
        """
        Get default LaTeX preamble.

        Returns:
            str: LaTeX preamble content
        """
        try:
            preamble = await self.preamble_repository.get_default()
            if not preamble:
                self.logger.warning("Default preamble not found, using empty string")
                return ""
            return preamble.content
        except Exception as e:
            self.logger.error(f"Error getting default preamble: {e}")
            return ""

    async def get_preamble(self, preamble_id: Union[str, None] = None) -> str:
        """
        Get LaTeX preamble by ID.

        Args:
            preamble_id: Preamble ID or None for default

        Returns:
            str: LaTeX preamble content
        """
        try:
            if not preamble_id:
                return await self.get_default_preamble()

            preamble = await self.preamble_repository.get_by_id(preamble_id)
            if not preamble:
                self.logger.warning(f"Preamble {preamble_id} not found, using default")
                return await self.get_default_preamble()
            return preamble.content
        except Exception as e:
            self.logger.error(f"Error getting preamble {preamble_id}: {e}")
            return await self.get_default_preamble()

    async def get_header(self, header_name: str = "default") -> str:
        """
        Get LaTeX header by name.

        Args:
            header_name: Header name

        Returns:
            str: LaTeX header content
        """
        try:
            header = await self.header_repository.get_by_name(header_name)
            if not header:
                self.logger.warning(
                    f"Header {header_name} not found, using empty string"
                )
                return ""
            return header.content
        except Exception as e:
            self.logger.error(f"Error getting header {header_name}: {e}")
            return ""

    async def get_template(self, template_name: str) -> str:
        """
        Get LaTeX template by name.

        Args:
            template_name: Template name

        Returns:
            str: LaTeX template content
        """
        try:
            template = await self.template_repository.get_by_name(template_name)
            if not template:
                self.logger.warning(
                    f"Template {template_name} not found, using empty string"
                )
                return ""
            return template.content
        except Exception as e:
            self.logger.error(f"Error getting template {template_name}: {e}")
            return ""

    async def generate_resume_latex(
        self,
        resume: Resume,
        profile: Profile,
        portfolio: Portfolio,
    ) -> str:
        """
        Generate LaTeX for a resume.

        Args:
            resume: Resume model
            profile: Profile model
            portfolio: Portfolio model

        Returns:
            str: LaTeX document
        """
        try:
            # Get template, header, and preamble
            template = await self.get_template("resume")
            header = await self.get_header(resume.template_id or "default")
            preamble = await self.get_default_preamble()

            # Extract content from resume
            content = resume.content or {}

            # Combine parameters
            params = {
                "header": header,
                "preamble": preamble,
                "name": profile.name if profile else "",
                "email": profile.email if profile else "",
                "phone": profile.phone if profile else "",
                "location": profile.location if profile else "",
                "links": self._format_links(profile.links if profile else {}),
                "summary": content.get("summary", ""),
                "skills": content.get("skills", ""),
                "work_experience": content.get("work_experience", ""),
                "education": content.get("education", ""),
                "projects": content.get("projects", ""),
                "awards": content.get("awards", ""),
                "publications": content.get("publications", ""),
            }

            # Format template
            return template.format(**params)

        except Exception as e:
            self.logger.error(f"Error generating resume LaTeX: {e}")
            raise InternalServerException(f"Failed to generate LaTeX: {str(e)}")

    async def generate_cover_letter_latex(
        self,
        resume: Resume,
        profile: Profile,
        portfolio: Portfolio,
    ) -> str:
        """
        Generate LaTeX for a cover letter.

        Args:
            resume: Resume model (containing cover letter content)
            profile: Profile model
            portfolio: Portfolio model

        Returns:
            str: LaTeX document
        """
        try:
            # Get template, header, and preamble
            template = await self.get_template("cover_letter")
            header = await self.get_header(resume.template_id or "default")
            preamble = await self.get_default_preamble()

            # Extract content
            content = resume.content or {}
            cover_letter_text = content.get("cover_letter", "")

            # Get application details
            company_name = resume.company_details or ""
            job_title = resume.job_position or ""

            # Combine parameters
            params = {
                "header": header,
                "preamble": preamble,
                "name": profile.name if profile else "",
                "email": profile.email if profile else "",
                "phone": profile.phone if profile else "",
                "location": profile.location if profile else "",
                "date": datetime.now().strftime("%B %d, %Y"),
                "company_name": company_name,
                "job_title": job_title,
                "cover_letter_text": cover_letter_text,
            }

            # Format template
            return template.format(**params)

        except Exception as e:
            self.logger.error(f"Error generating cover letter LaTeX: {e}")
            raise InternalServerException(f"Failed to generate LaTeX: {str(e)}")

    def _format_links(self, links: Dict[str, str]) -> str:
        """
        Format links for LaTeX.

        Args:
            links: Dictionary of links

        Returns:
            str: Formatted links
        """
        if not links:
            return ""

        formatted_links = []
        for name, url in links.items():
            if url:
                formatted_links.append(f"\\href{{{url}}}{{{name}}}")

        return " | ".join(formatted_links)

    async def compile_latex_to_pdf(
        self, latex_content: str, is_cover_letter: bool = False
    ) -> bytes:
        """
        Compile LaTeX content to PDF.

        Args:
            latex_content: LaTeX content
            is_cover_letter: Whether the content is for a cover letter

        Returns:
            bytes: PDF content

        Raises:
            InternalServerException: If compilation fails
        """
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create temporary file path
                tex_path = Path(temp_dir) / "document.tex"

                # Use the appropriate compiler based on document type
                compiler = (
                    self.cover_letter_compiler
                    if is_cover_letter
                    else self.resume_compiler
                )

                # Compile the LaTeX content
                pdf_content = await compiler.compile_pdf(tex_path, latex_content)

                if pdf_content is None:
                    raise InternalServerException("LaTeX compilation failed")

                return pdf_content

        except Exception as e:
            self.logger.error(f"Error compiling LaTeX: {e}")
            raise InternalServerException(f"Error compiling LaTeX: {str(e)}")

    async def clear_caches(self) -> None:
        """Clear all repository caches."""
        await self.template_repository.clear_cache()
        await self.header_repository.clear_cache()
        await self.preamble_repository.clear_cache()
