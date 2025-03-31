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

            # Import repository here to avoid circular imports
            from core.repositories.tex_header_repository import (
                get_tex_header_repository,
            )

            tex_header_repo = get_tex_header_repository()

            # Get personal information
            info = cover_letter.personal_information or {}
            full_name = sanitize_latex(info.get("full_name", ""))
            email = sanitize_latex(info.get("email", ""))
            phone = sanitize_latex(info.get("phone", ""))
            address = sanitize_latex(info.get("address", ""))
            linkedin = sanitize_latex(info.get("linkedin", ""))
            github = sanitize_latex(info.get("github", ""))
            website = sanitize_latex(info.get("website", ""))

            # Get cover letter content
            company_name = sanitize_latex(cover_letter.company_name or "")
            job_title = sanitize_latex(cover_letter.job_title or "")
            cover_letter_text = sanitize_latex(cover_letter.cover_letter_content or "")

            # Format the date
            from datetime import datetime

            date = datetime.now().strftime("%B %d, %Y")

            # Prepare placeholders
            placeholders = {
                "NAME": full_name,
                "EMAIL": email,
                "PHONE": phone,
                "ADDRESS": address,
                "LINKEDIN": linkedin,
                "GITHUB": github,
                "WEBSITE": website,
                "DATE": date,
                "COMPANY_NAME": company_name,
                "JOB_TITLE": job_title,
                "COVER_LETTER_CONTENT": cover_letter_text,
            }

            # Try to get the cover letter template
            cover_letter_template = None
            try:
                # Check if a specific template is set
                if cover_letter.template_id:
                    cover_letter_template = await tex_header_repo.get_by_name(
                        cover_letter.template_id
                    )

                # If no specific template or template not found, get default
                if not cover_letter_template:
                    cover_letter_template = await tex_header_repo.get_default(
                        "cover_letter"
                    )
            except Exception as e:
                self.logger.error(f"Error retrieving cover letter template: {e}")

            # Apply header template if provided in parameters
            if (
                "header" in template["section_formats"]
                and template["section_formats"]["header"]
            ):
                # Use the provided header template
                header_content = self.placeholder_manager.replace_placeholders(
                    template["section_formats"]["header"],
                    placeholders,
                )
                content.append(header_content)
            elif cover_letter_template:
                # Use the template from the database
                self.logger.debug(
                    f"Using cover letter template: {cover_letter_template.name}"
                )
                header_content = self.placeholder_manager.replace_placeholders(
                    cover_letter_template.content,
                    placeholders,
                )
                content.append(header_content)
            else:
                # Fallback to a basic cover letter structure
                self.logger.warning("No cover letter template found, using fallback")
                content.append(f"\\begin{{letter}}{{{company_name}}}")
                content.append("\\opening{Dear Hiring Manager,}")
                content.append(cover_letter_text)
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
