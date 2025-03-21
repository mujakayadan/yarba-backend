"""Cover letter compiler implementation."""

from pathlib import Path
from typing import Any, Dict, Optional

from ...models.resume import Resume
from ..base import LatexCompiler
from ..utils.placeholder import PlaceholderManager
from ..utils.sanitizer import sanitize_latex


class CoverLetterCompiler(LatexCompiler):
    """Cover letter compiler for generating PDF cover letters.

    This class handles the compilation of cover letter data into LaTeX format
    and then into PDF. It uses templates and placeholder substitution
    to generate the final document.
    """

    def __init__(self):
        """Initialize the cover letter compiler."""
        super().__init__()
        self.placeholder_manager = PlaceholderManager()

    async def generate_tex_content(
        self, resume: Resume, template: Dict[str, Any]
    ) -> str:
        """Generate LaTeX content for a cover letter.

        Args:
            resume: Resume data (containing cover letter content)
            template: LaTeX template data

        Returns:
            str: Generated LaTeX content
        """
        # Start with document class and packages
        content = [
            f"\\documentclass[{template['header']['font_size']}]{{{template['header']['document_class']}}}",
            "\\usepackage{geometry}",
            f"\\geometry{{margin={template['header']['margin_size']}}}",
        ]

        # Add required packages
        for package in template["header"]["packages"]:
            content.append(f"\\usepackage{{{package}}}")

        # Add custom commands
        for cmd, def_ in template["header"]["custom_commands"].items():
            content.append(f"\\newcommand{{{cmd}}}{def_}")

        # Begin document
        content.append("\\begin{document}")

        # Add personal information
        content.append(self._generate_personal_info_section(resume, template))

        # Add current date
        content.append("\\today")
        content.append("\\vspace{1em}")

        # Add recipient information if available
        if "recipient" in resume.personal_information:
            recipient = resume.personal_information["recipient"]
            content.extend(
                [
                    sanitize_latex(recipient.get("name", "")),
                    sanitize_latex(recipient.get("title", "")),
                    sanitize_latex(recipient.get("company", "")),
                    sanitize_latex(recipient.get("address", "")),
                    "\\vspace{1em}",
                ]
            )

        # Add salutation
        content.append("Dear Hiring Manager,")
        content.append("\\vspace{1em}")

        # Add cover letter content
        if resume.cover_letter_content:
            paragraphs = resume.cover_letter_content.split("\n\n")
            for paragraph in paragraphs:
                content.append(sanitize_latex(paragraph))
                content.append("\\vspace{1em}")

        # Add closing
        content.extend(
            [
                "\\vspace{1em}",
                "Sincerely,",
                "\\vspace{2em}",
                sanitize_latex(resume.personal_information.get("name", "")),
            ]
        )

        # End document
        content.append("\\end{document}")

        return "\n".join(content)

    def _generate_personal_info_section(
        self, resume: Resume, template: Dict[str, Any]
    ) -> str:
        """Generate the personal information section.

        Args:
            resume: Resume data
            template: LaTeX template data

        Returns:
            str: Generated LaTeX content for personal information
        """
        info = resume.personal_information
        placeholders = {
            "name": sanitize_latex(info.get("name", "")),
            "email": sanitize_latex(info.get("email", "")),
            "phone": sanitize_latex(info.get("phone", "")),
            "address": sanitize_latex(info.get("address", "")),
            "linkedin": sanitize_latex(info.get("linkedin", "")),
        }

        return self.placeholder_manager.replace_placeholders(
            template["section_formats"]["header"],
            placeholders,
        )

    async def generate_pdf(
        self, resume: Resume, template: Dict[str, Any]
    ) -> Optional[bytes]:
        """Generate a PDF from a cover letter.

        Args:
            resume: Resume data (containing cover letter content)
            template: LaTeX template data

        Returns:
            Optional[bytes]: PDF content if successful, None otherwise
        """
        # Generate LaTeX content
        tex_content = await self.generate_tex_content(resume, template)

        # Create temporary file path
        tex_path = Path(self.output_dir) / f"{resume.id}_cover_letter.tex"

        # Compile to PDF
        return await self.compile_pdf(tex_path, tex_content)
