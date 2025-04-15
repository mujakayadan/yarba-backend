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
            template: LaTeX template data containing personal_info, company_name, job_title, and cover_letter_content

        Returns:
            str: Generated LaTeX content
        """
        try:
            # Get personal information from template
            personal_info = template.get("personal_info", {})
            name = sanitize_latex(personal_info.get("name", ""))
            phone = sanitize_latex(personal_info.get("phone", ""))
            email = sanitize_latex(personal_info.get("email", ""))
            linkedin = sanitize_latex(personal_info.get("linkedin", "#"))
            github = sanitize_latex(personal_info.get("github", "#"))
            website = sanitize_latex(personal_info.get("website", "#"))
            address = sanitize_latex(personal_info.get("address", ""))

            # Get job information from template
            company_name = sanitize_latex(template.get("company_name", ""))
            job_title = sanitize_latex(template.get("job_title", ""))

            # Get cover letter content from template
            cover_letter_content = sanitize_latex(
                template.get("cover_letter_content", "")
            )

            # Get the template preamble or use default
            preamble = DEFAULT_COVER_LETTER_PREAMBLE
            if template and "header" in template and "preamble" in template["header"]:
                preamble = template["header"]["preamble"]

            # Generate the closing for the letter (including today's date but without signature image)
            closing = """
\\vspace{0.3cm}
\\today
\\end{letter}
\\end{document}"""

            # Replace placeholders in the cover letter
            return (
                (
                    preamble
                    + """
\\begin{document}
\\begin{letter}{{{COMPANY_NAME}} \\\\ {{JOB_TITLE}}}

\\personalInformation{{{NAME}}}{{{PHONE}}}{{{EMAIL}}}{{{LINKEDIN}}}{{{GITHUB}}}{{{WEBSITE}}}{{{ADDRESS}}}

\\vspace{0.3cm}
\\justifying  % Enable justification for the letter content

{{COVER_LETTER_CONTENT}}

"""
                    + closing
                )
                .replace("{{NAME}}", name)
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
