"""LaTeX service for LaTeX document generation."""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from config.logging_config import get_logger
from config.settings import Settings
from core.exceptions.base import InternalServerException
from core.latex.compilers import CoverLetterCompiler, ResumeCompiler
from core.latex.config import LatexConfig
from core.models.resume import Resume
from core.repositories.preamble import PreambleRepository
from core.repositories.tex_header import TexHeaderRepository
from core.repositories.tex_template import TexTemplateRepository

settings = Settings()
logger = get_logger(__name__)


class LatexService:
    """Service for LaTeX document generation."""

    def __init__(
        self,
        template_repository: Optional[TexTemplateRepository] = None,
        header_repository: Optional[TexHeaderRepository] = None,
        preamble_repository: Optional[PreambleRepository] = None,
        latex_config: Optional[LatexConfig] = None,
    ):
        """
        Initialize the LaTeX service.

        Args:
            template_repository: Repository for accessing LaTeX templates
            header_repository: Repository for accessing LaTeX headers
            preamble_repository: Repository for accessing LaTeX preambles
            latex_config: Configuration for LaTeX compilation
        """
        self.template_repository = template_repository or TexTemplateRepository()
        self.header_repository = header_repository or TexHeaderRepository()
        self.preamble_repository = preamble_repository or PreambleRepository()
        self.latex_config = latex_config or LatexConfig()
        self.logger = get_logger(self.__class__.__name__)

        # Initialize the compilers
        self.resume_compiler = ResumeCompiler(self.latex_config)
        self.cover_letter_compiler = CoverLetterCompiler(self.latex_config)

    async def get_template(self, template_name: str) -> str:
        """
        Get a LaTeX template by name.

        Args:
            template_name: Template name

        Returns:
            str: Template content
        """
        return await self.template_repository.get_by_name(template_name)

    async def get_header(self, header_name: str) -> str:
        """
        Get a LaTeX header by name.

        Args:
            header_name: Header name

        Returns:
            str: Header content
        """
        return await self.header_repository.get_by_name(header_name)

    async def get_default_header(self) -> str:
        """
        Get the default LaTeX header.

        Returns:
            str: Default header content
        """
        return await self.header_repository.get_default()

    async def get_default_preamble(self) -> str:
        """
        Get the default LaTeX preamble.

        Returns:
            str: Default preamble content
        """
        return await self.preamble_repository.get_default()

    async def format_template(self, template_name: str, params: Dict[str, Any]) -> str:
        """
        Format a LaTeX template with parameters.

        Args:
            template_name: Template name
            params: Template parameters

        Returns:
            str: Formatted template content
        """
        return await self.template_repository.safe_format_template(
            template_name, params
        )

    async def generate_resume_latex(
        self,
        resume: Resume,
        profile_data: Dict[str, Any],
        portfolio_data: Dict[str, Any],
        content: Dict[str, str],
    ) -> str:
        """
        Generate LaTeX for a resume.

        Args:
            resume: Resume model
            profile_data: Profile data
            portfolio_data: Portfolio data
            content: Generated content for sections

        Returns:
            str: LaTeX document
        """
        try:
            # Get template, header, and preamble
            template = await self.get_template("resume")
            header = await self.get_header(resume.template_name or "modern")
            preamble = await self.get_default_preamble()

            # Combine parameters
            params = {
                "header": header,
                "preamble": preamble,
                "name": profile_data.get("name", ""),
                "email": profile_data.get("email", ""),
                "phone": profile_data.get("phone", ""),
                "location": profile_data.get("location", ""),
                "links": self._format_links(profile_data.get("links", {})),
                "summary": content.get("summary", ""),
                "skills": content.get("skills", ""),
                "work_experience": content.get("work_experience", ""),
                "education": content.get("education", ""),
                "projects": content.get("projects", ""),
                "awards": content.get("awards", ""),
                "publications": content.get("publications", ""),
            }

            # Format template
            return await self.format_template(template_name="resume", params=params)

        except Exception as e:
            self.logger.error(f"Error generating resume LaTeX: {e}")
            raise InternalServerException(f"Failed to generate LaTeX: {str(e)}")

    async def generate_cover_letter_latex(
        self,
        profile_data: Dict[str, Any],
        company_name: str,
        job_title: str,
        content: str,
    ) -> str:
        """
        Generate LaTeX for a cover letter.

        Args:
            profile_data: Profile data
            company_name: Company name
            job_title: Job title
            content: Cover letter content

        Returns:
            str: LaTeX document
        """
        try:
            # Get template, header, and preamble
            template = await self.get_template("cover_letter")
            header = await self.get_default_header()
            preamble = await self.get_default_preamble()

            # Get current date
            from datetime import datetime

            current_date = datetime.now().strftime("%B %d, %Y")

            # Combine parameters
            params = {
                "header": header,
                "preamble": preamble,
                "name": profile_data.get("name", ""),
                "email": profile_data.get("email", ""),
                "phone": profile_data.get("phone", ""),
                "address": profile_data.get("location", ""),
                "date": current_date,
                "company_name": company_name,
                "job_title": job_title,
                "content": content,
            }

            # Format template
            return await self.format_template(
                template_name="cover_letter", params=params
            )

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
