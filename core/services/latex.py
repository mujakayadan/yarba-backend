"""LaTeX service for LaTeX document generation."""

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..exceptions.base import InternalServerException
from ..models.latex import Preamble, TexHeader, TexTemplate
from ..models.resume import Resume
from ..repositories.latex import (
    PreambleRepository,
    TexHeaderRepository,
    TexTemplateRepository,
)
from .config import settings

logger = logging.getLogger(__name__)


class LaTeXService:
    """Service for handling LaTeX document generation."""

    def __init__(
        self,
        tex_template_repository: TexTemplateRepository,
        tex_header_repository: TexHeaderRepository,
        preamble_repository: PreambleRepository,
    ):
        """
        Initialize the service.

        Args:
            tex_template_repository: TeX template repository instance
            tex_header_repository: TeX header repository instance
            preamble_repository: Preamble repository instance
        """
        self.tex_template_repository = tex_template_repository
        self.tex_header_repository = tex_header_repository
        self.preamble_repository = preamble_repository
        self.logger = logging.getLogger(self.__class__.__name__)

        # Register default templates
        self.tex_template_repository.register_default_templates()

    def get_template(self, template_name: str) -> Optional[TexTemplate]:
        """
        Get a LaTeX template by name.

        Args:
            template_name: Template name

        Returns:
            Optional[TexTemplate]: Template if found, None otherwise
        """
        return self.tex_template_repository.get_by_name(template_name)

    def get_all_templates(self) -> List[TexTemplate]:
        """
        Get all LaTeX templates.

        Returns:
            List[TexTemplate]: List of templates
        """
        return self.tex_template_repository.get_all()

    def generate_latex_document(self, resume: Resume) -> str:
        """
        Generate a LaTeX document from a resume.

        Args:
            resume: Resume

        Returns:
            str: LaTeX document

        Raises:
            InternalServerException: If template not found
        """
        # Get template
        template = self.get_template(resume.template_id)
        if not template:
            self.logger.error(f"Template not found: {resume.template_id}")
            raise InternalServerException(f"Template not found: {resume.template_id}")

        # Generate LaTeX document
        latex = template.to_latex()

        # Add document content
        if resume.is_latex_format():
            # Resume content is already in LaTeX format
            latex += "\\begin{document}\n\n"
            latex += resume.get_combined_latex()
            latex += "\n\n\\end{document}"
        else:
            # Resume content is in structured format, convert to LaTeX
            latex += "\\begin{document}\n\n"

            # Add personal information
            if resume.personal_information:
                latex += self._format_personal_information(resume.personal_information)

            # Add career summary
            if resume.career_summary:
                latex += "\\section*{Career Summary}\n"
                latex += resume.career_summary
                latex += "\n\n"

            # Add skills
            if resume.skills:
                latex += self._format_skills(resume.skills)

            # Add work experience
            if resume.work_experience:
                latex += self._format_work_experience(resume.work_experience)

            # Add education
            if resume.education:
                latex += self._format_education(resume.education)

            # Add projects
            if resume.projects:
                latex += self._format_projects(resume.projects)

            # Add awards
            if resume.awards:
                latex += self._format_awards(resume.awards)

            # Add publications
            if resume.publications:
                latex += self._format_publications(resume.publications)

            latex += "\\end{document}"

        return latex

    def compile_latex_to_pdf(self, latex_content: str) -> bytes:
        """
        Compile LaTeX content to PDF.

        Args:
            latex_content: LaTeX content

        Returns:
            bytes: PDF content

        Raises:
            InternalServerException: If compilation fails
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create temporary files
            tex_file = Path(temp_dir) / "document.tex"
            pdf_file = Path(temp_dir) / "document.pdf"

            # Write LaTeX content to file
            tex_file.write_text(latex_content)

            try:
                # Compile LaTeX to PDF
                result = subprocess.run(
                    [
                        "pdflatex",
                        "-interaction=nonstopmode",
                        "-output-directory",
                        temp_dir,
                        str(tex_file),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                # Check if compilation was successful
                if result.returncode != 0:
                    self.logger.error(f"LaTeX compilation failed: {result.stderr}")
                    raise InternalServerException("LaTeX compilation failed")

                # Run pdflatex again to resolve references
                subprocess.run(
                    [
                        "pdflatex",
                        "-interaction=nonstopmode",
                        "-output-directory",
                        temp_dir,
                        str(tex_file),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                # Read PDF content
                if pdf_file.exists():
                    return pdf_file.read_bytes()
                else:
                    self.logger.error("PDF file not found after compilation")
                    raise InternalServerException(
                        "PDF file not found after compilation"
                    )

            except Exception as e:
                self.logger.error(f"Error compiling LaTeX: {str(e)}")
                raise InternalServerException(f"Error compiling LaTeX: {str(e)}")

    def generate_pdf_from_resume(self, resume: Resume) -> bytes:
        """
        Generate a PDF from a resume.

        Args:
            resume: Resume

        Returns:
            bytes: PDF content

        Raises:
            InternalServerException: If generation fails
        """
        try:
            # Generate LaTeX document
            latex = self.generate_latex_document(resume)

            # Compile LaTeX to PDF
            pdf = self.compile_latex_to_pdf(latex)

            return pdf

        except Exception as e:
            self.logger.error(f"Error generating PDF: {str(e)}")
            raise InternalServerException(f"Error generating PDF: {str(e)}")

    def _format_personal_information(self, personal_info: Dict[str, str]) -> str:
        """
        Format personal information as LaTeX.

        Args:
            personal_info: Personal information

        Returns:
            str: LaTeX content
        """
        latex = "\\begin{center}\n"

        if "name" in personal_info:
            latex += f"\\textbf{{\\Large {personal_info['name']}}}\\\\\n"

        address_parts = []
        if "address" in personal_info:
            address_parts.append(personal_info["address"])
        if (
            "city" in personal_info
            and "state" in personal_info
            and "zip" in personal_info
        ):
            address_parts.append(
                f"{personal_info['city']}, {personal_info['state']} {personal_info['zip']}"
            )

        if address_parts:
            latex += f"{' '.join(address_parts)}\\\\\n"

        contact_parts = []
        if "phone" in personal_info:
            contact_parts.append(personal_info["phone"])
        if "email" in personal_info:
            contact_parts.append(personal_info["email"])
        if "linkedin" in personal_info:
            contact_parts.append(personal_info["linkedin"])

        if contact_parts:
            latex += f"{' | '.join(contact_parts)}\n"

        latex += "\\end{center}\n\n"

        return latex

    def _format_skills(self, skills: Dict[str, List[str]]) -> str:
        """
        Format skills as LaTeX.

        Args:
            skills: Skills

        Returns:
            str: LaTeX content
        """
        latex = "\\section*{Skills}\n"

        for category, skill_list in skills.items():
            latex += f"\\textbf{{{category}}}: {', '.join(skill_list)}\\\\\n"

        latex += "\n"

        return latex

    def _format_work_experience(self, work_experience: List[Dict]) -> str:
        """
        Format work experience as LaTeX.

        Args:
            work_experience: Work experience

        Returns:
            str: LaTeX content
        """
        latex = "\\section*{Work Experience}\n"
        latex += "\\begin{itemize}[leftmargin=*]\n"

        for job in work_experience:
            company = job.get("company", "")
            position = job.get("position", "")
            start_date = job.get("start_date", "")
            end_date = job.get(
                "end_date", "Present" if job.get("current", False) else ""
            )

            latex += (
                f"\\item \\textbf{{{company}}} \\hfill {start_date} -- {end_date}\\\\\n"
            )
            latex += f"\\textit{{{position}}}\n"

            if "responsibilities" in job and job["responsibilities"]:
                latex += "\\begin{itemize}\n"
                for responsibility in job["responsibilities"]:
                    latex += f"\\item {responsibility}\n"
                latex += "\\end{itemize}\n"

        latex += "\\end{itemize}\n\n"

        return latex

    def _format_education(self, education: List[Dict]) -> str:
        """
        Format education as LaTeX.

        Args:
            education: Education

        Returns:
            str: LaTeX content
        """
        latex = "\\section*{Education}\n"
        latex += "\\begin{itemize}[leftmargin=*]\n"

        for edu in education:
            institution = edu.get("institution", "")
            degree = edu.get("degree", "")
            field = edu.get("field_of_study", "")
            start_date = edu.get("start_date", "")
            end_date = edu.get(
                "end_date", "Present" if edu.get("current", False) else ""
            )
            gpa = edu.get("gpa", "")

            latex += f"\\item \\textbf{{{institution}}} \\hfill {start_date} -- {end_date}\\\\\n"
            latex += f"{degree} in {field}"

            if gpa:
                latex += f" \\hfill \\textit{{GPA: {gpa}}}"

            latex += "\n"

            if "courses" in edu and edu["courses"]:
                latex += f"\\textit{{Relevant Courses:}} {', '.join(edu['courses'])}\n"

        latex += "\\end{itemize}\n\n"

        return latex

    def _format_projects(self, projects: List[Dict]) -> str:
        """
        Format projects as LaTeX.

        Args:
            projects: Projects

        Returns:
            str: LaTeX content
        """
        latex = "\\section*{Projects}\n"
        latex += "\\begin{itemize}[leftmargin=*]\n"

        for project in projects:
            name = project.get("name", "")
            description = project.get("description", "")

            latex += f"\\item \\textbf{{{name}}}\\\\\n"
            latex += f"{description}\n"

            if "technologies" in project and project["technologies"]:
                latex += (
                    f"\\textit{{Technologies:}} {', '.join(project['technologies'])}\n"
                )

        latex += "\\end{itemize}\n\n"

        return latex

    def _format_awards(self, awards: List[Dict]) -> str:
        """
        Format awards as LaTeX.

        Args:
            awards: Awards

        Returns:
            str: LaTeX content
        """
        latex = "\\section*{Awards}\n"
        latex += "\\begin{itemize}[leftmargin=*]\n"

        for award in awards:
            title = award.get("title", "")
            issuer = award.get("issuer", "")
            date = award.get("date", "")

            latex += f"\\item \\textbf{{{title}}}"

            if issuer:
                latex += f", {issuer}"

            if date:
                latex += f" \\hfill {date}"

            latex += "\n"

        latex += "\\end{itemize}\n\n"

        return latex

    def _format_publications(self, publications: List[Dict]) -> str:
        """
        Format publications as LaTeX.

        Args:
            publications: Publications

        Returns:
            str: LaTeX content
        """
        latex = "\\section*{Publications}\n"
        latex += "\\begin{itemize}[leftmargin=*]\n"

        for publication in publications:
            title = publication.get("title", "")
            authors = publication.get("authors", "")
            journal = publication.get("journal", "")
            date = publication.get("date", "")

            latex += f"\\item \\textbf{{{title}}}"

            if authors:
                latex += f"\\\\\n{authors}"

            if journal:
                latex += f", {journal}"

            if date:
                latex += f" ({date})"

            latex += "\n"

        latex += "\\end{itemize}\n\n"

        return latex
