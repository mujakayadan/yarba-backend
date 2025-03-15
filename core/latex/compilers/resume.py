"""Resume compiler implementation."""

from pathlib import Path
from typing import Any, Dict, Optional

from ...models.resume import Resume
from ..base import LatexCompiler
from ..config import LatexConfig
from ..utils.placeholder import PlaceholderManager
from ..utils.sanitizer import sanitize_latex


class ResumeCompiler(LatexCompiler):
    """Resume compiler for generating PDF resumes.

    This class handles the compilation of resume data into LaTeX format
    and then into PDF. It uses templates and placeholder substitution
    to generate the final document.
    """

    def __init__(self, config: Optional[LatexConfig] = None):
        """Initialize the resume compiler.

        Args:
            config: Optional LaTeX configuration
        """
        super().__init__(config)
        self.placeholder_manager = PlaceholderManager()

    async def generate_tex_content(
        self, resume: Resume, template: Dict[str, Any]
    ) -> str:
        """Generate LaTeX content for a resume.

        Args:
            resume: Resume data
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

        # Add career summary if available
        if resume.career_summary:
            content.append("\\section*{Career Summary}")
            content.append(sanitize_latex(resume.career_summary))

        # Add skills
        if resume.skills:
            content.append("\\section*{Skills}")
            for category, skills in resume.skills.items():
                content.append(
                    f"\\textbf{{{category}}}: {', '.join(sanitize_latex(skill) for skill in skills)}"
                )

        # Add work experience
        if resume.work_experience:
            content.append("\\section*{Work Experience}")
            for exp in resume.work_experience:
                content.extend(
                    [
                        f"\\textbf{{{sanitize_latex(exp['company'])}}} \\hfill {exp['start_date']} -- {exp['end_date']}",
                        f"\\textit{{{sanitize_latex(exp['position'])}}}",
                        "\\begin{itemize}",
                        *[
                            f"\\item {sanitize_latex(resp)}"
                            for resp in exp["responsibilities"]
                        ],
                        "\\end{itemize}",
                    ]
                )

        # Add education
        if resume.education:
            content.append("\\section*{Education}")
            for edu in resume.education:
                content.extend(
                    [
                        f"\\textbf{{{sanitize_latex(edu['institution'])}}} \\hfill {edu['start_date']} -- {edu['end_date']}",
                        f"{sanitize_latex(edu['degree'])} in {sanitize_latex(edu['field_of_study'])}",
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
        """Generate a PDF from a resume.

        Args:
            resume: Resume data
            template: LaTeX template data

        Returns:
            Optional[bytes]: PDF content if successful, None otherwise
        """
        # Generate LaTeX content
        tex_content = await self.generate_tex_content(resume, template)

        # Create temporary file path
        tex_path = Path(self.config.output_dir) / f"{resume.id}.tex"

        # Compile to PDF
        return await self.compile_pdf(tex_path, tex_content)
