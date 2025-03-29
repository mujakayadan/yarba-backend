"""Cover letter compiler implementation."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from ...models.cover_letter import CoverLetter
from ..base import LatexCompiler
from ..utils.placeholder import PlaceholderManager
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
        self.placeholder_manager = PlaceholderManager()

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
            # Start with document class and packages
            content = []

            # Use preamble directly since it already contains document class, packages, etc.
            if "preamble" in template["header"] and template["header"]["preamble"]:
                # Use the provided preamble
                content.append(template["header"]["preamble"])
            else:
                # Fallback to a basic preamble if none provided
                self.logger.warning(
                    "No preamble provided, using fallback basic preamble"
                )
                content.append("\\documentclass[12pt]{letter}")
                content.append("\\usepackage{geometry}")
                content.append("\\usepackage{hyperref}")
                # Ensure we have a document start
                content.append("\\begin{document}")

            # Begin document if not already included in preamble
            if "\\begin{document}" not in template["header"]["preamble"]:
                content.append("\\begin{document}")

            # Get personal information
            info = cover_letter.personal_information or {}
            full_name = info.get("full_name", "")
            email = info.get("email", "")
            phone = info.get("phone", "")
            address = info.get("address", "")
            linkedin = info.get("linkedin", "")
            github = info.get("github", "")
            website = info.get("website", "")

            # Get cover letter content
            company_name = cover_letter.company_name or ""
            job_title = cover_letter.job_title or ""
            cover_letter_text = cover_letter.cover_letter_content or ""

            # Format the date
            from datetime import datetime

            date = datetime.now().strftime("%B %d, %Y")

            # Apply header template if provided
            if (
                "header" in template["section_formats"]
                and template["section_formats"]["header"]
            ):
                # Replace placeholders in header template
                placeholders = {
                    "NAME": sanitize_latex(full_name),
                    "EMAIL": sanitize_latex(email),
                    "PHONE": sanitize_latex(phone),
                    "ADDRESS": sanitize_latex(address),
                    "LINKEDIN": sanitize_latex(linkedin),
                    "GITHUB": sanitize_latex(github),
                    "WEBSITE": sanitize_latex(website),
                    "DATE": date,
                    "COMPANY_NAME": sanitize_latex(company_name),
                    "JOB_TITLE": sanitize_latex(job_title),
                    "COVER_LETTER_CONTENT": sanitize_latex(cover_letter_text),
                }
                header_content = self.placeholder_manager.replace_placeholders(
                    template["section_formats"]["header"],
                    placeholders,
                )
                content.append(header_content)
            else:
                # Create a basic cover letter structure
                content.append(f"\\begin{{letter}}{{{sanitize_latex(company_name)}}}")
                content.append("\\opening{Dear Hiring Manager,}")
                content.append(sanitize_latex(cover_letter_text))
                content.append("\\closing{Sincerely,}")
                content.append(full_name)
                content.append("\\end{letter}")

            # End document if not already included in preamble
            if "\\end{document}" not in template["header"]["preamble"]:
                content.append("\\end{document}")

            # Join all lines
            return "\n".join(content)

        except Exception as e:
            self.logger.error(f"Error generating cover letter LaTeX content: {e}")
            raise

    async def generate_pdf(
        self, cover_letter: CoverLetter, template: Dict[str, Any]
    ) -> Optional[bytes]:
        """Generate a PDF from a cover letter.

        Args:
            cover_letter: Cover letter data
            template: LaTeX template data

        Returns:
            Optional[bytes]: PDF content if successful, None otherwise
        """
        # Generate LaTeX content
        tex_content = await self.generate_tex_content(cover_letter, template)

        # Create temporary file path
        tex_path = Path(self.output_dir) / f"{cover_letter.id}.tex"

        # Compile to PDF
        return await self.compile_pdf(tex_path, tex_content)
