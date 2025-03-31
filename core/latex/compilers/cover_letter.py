"""Cover letter compiler implementation."""

import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from ...models.cover_letter import CoverLetter
from ..base import LatexCompiler
from ..templates import DEFAULT_COVER_LETTER_PREAMBLE
from ..utils.sanitizer import sanitize_latex


class CoverLetterCompiler(LatexCompiler):
    """Cover letter compiler for generating PDF cover letters.

    This class handles the compilation of cover letter data into LaTeX format
    and then into PDF. It uses templates and placeholder substitution to
    generate the final document.
    """

    def __init__(self):
        """Initialize the cover letter compiler."""
        super().__init__()

    async def generate_tex_content(
        self, cover_letter: CoverLetter, template: Dict[str, Any]
    ) -> str:
        """Generate LaTeX content for a cover letter.

        Args:
            cover_letter: Cover letter data
            template: LaTeX template data

        Returns:
            str: Generated LaTeX content
        """
        try:
            # Get personal information from cover_letter
            name = sanitize_latex(
                cover_letter.name if hasattr(cover_letter, "name") else ""
            )
            phone = sanitize_latex(
                cover_letter.phone if hasattr(cover_letter, "phone") else ""
            )
            email = sanitize_latex(
                cover_letter.email if hasattr(cover_letter, "email") else ""
            )
            linkedin = sanitize_latex(
                cover_letter.linkedin if hasattr(cover_letter, "linkedin") else "#"
            )
            github = sanitize_latex(
                cover_letter.github if hasattr(cover_letter, "github") else "#"
            )
            website = sanitize_latex(
                cover_letter.website if hasattr(cover_letter, "website") else "#"
            )
            address = sanitize_latex(
                cover_letter.address if hasattr(cover_letter, "address") else ""
            )

            # Get job information
            company_name = sanitize_latex(cover_letter.company_name or "")
            job_title = sanitize_latex(cover_letter.job_title or "")

            # Get cover letter content
            cover_letter_content = sanitize_latex(
                cover_letter.cover_letter_content or ""
            )

            # Get the template preamble or use default
            preamble = DEFAULT_COVER_LETTER_PREAMBLE
            if template and "header" in template and "preamble" in template["header"]:
                preamble = template["header"]["preamble"]

            # Replace placeholders in the cover letter
            return (
                preamble.replace("{{NAME}}", name)
                .replace("{{PHONE}}", phone)
                .replace("{{EMAIL}}", email)
                .replace("{{LINKEDIN}}", linkedin)
                .replace("{{GITHUB}}", github)
                .replace("{{WEBSITE}}", website)
                .replace("{{ADDRESS}}", address)
                .replace("{{COMPANY_NAME}}", company_name)
                .replace("{{JOB_TITLE}}", job_title)
                .replace("{{COVER_LETTER_CONTENT}}", cover_letter_content)
            )

        except Exception as e:
            self.logger.error(f"Error generating LaTeX content: {e}")
            raise

    async def generate_pdf(
        self, cover_letter: CoverLetter, template: Dict[str, Any]
    ) -> Optional[bytes]:
        """Generate a PDF file from a cover letter.

        Args:
            cover_letter: Cover letter data
            template: LaTeX template data

        Returns:
            Optional[bytes]: PDF content if successful, None otherwise
        """
        try:
            # Generate LaTeX content
            latex_content = await self.generate_tex_content(cover_letter, template)

            # Create a temp file for LaTeX compilation
            with tempfile.NamedTemporaryFile(suffix=".tex", delete=False) as temp_file:
                temp_path = Path(temp_file.name)

            # Compile to PDF
            pdf_content = await self.compile_pdf(temp_path, latex_content)

            return pdf_content

        except Exception as e:
            self.logger.error(f"Error generating PDF: {e}")
            return None
