"""Resume compiler implementation."""

from pathlib import Path
from typing import Any, Dict, Optional

from ...models.resume import Resume
from ..base import LatexCompiler
from ..utils.placeholder import PlaceholderManager
from ..utils.sanitizer import sanitize_latex


class ResumeCompiler(LatexCompiler):
    """Resume compiler for generating PDF resumes.

    This class handles the compilation of resume data into LaTeX format
    and then into PDF. It uses templates and placeholder substitution
    to generate the final document.
    """

    def __init__(self):
        """Initialize the resume compiler."""
        super().__init__()
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
        try:
            # Start with document class and packages
            content = []

            # Use preamble if provided in template
            if "preamble" in template["header"] and template["header"]["preamble"]:
                # Use the provided preamble
                content.append(template["header"]["preamble"])
            else:
                # Otherwise use standard documentclass and packages
                content.append(
                    f"\\documentclass[{template['header']['font_size']}]{{{template['header']['document_class']}}}"
                )
                content.append("\\usepackage{geometry}")
                content.append(
                    f"\\geometry{{margin={template['header']['margin_size']}}}"
                )

                # Add required packages
                for package in template["header"]["packages"]:
                    content.append(f"\\usepackage{{{package}}}")

                # Add custom commands
                for cmd, def_ in template["header"]["custom_commands"].items():
                    content.append(f"\\newcommand{{{cmd}}}{def_}")

            # Begin document
            if "\\begin{document}" not in content[-1]:
                content.append("\\begin{document}")

            # Add personal information
            content.append(self._generate_personal_info_section(resume, template))

            # Process content sections - try both direct attributes and content dictionary
            # Career Summary
            career_summary = None
            if hasattr(resume, "career_summary") and resume.career_summary:
                career_summary = resume.career_summary
            elif (
                hasattr(resume, "content")
                and isinstance(resume.content, dict)
                and "career_summary" in resume.content
            ):
                career_summary = resume.content["career_summary"]

            if career_summary:
                content.append("\\section*{Career Summary}")
                content.append(sanitize_latex(career_summary))

            # Skills
            skills = None
            if hasattr(resume, "skills") and resume.skills:
                skills = resume.skills
            elif (
                hasattr(resume, "content")
                and isinstance(resume.content, dict)
                and "skills" in resume.content
            ):
                skills = resume.content["skills"]

            if skills:
                content.append("\\section*{Skills}")
                # Handle both dictionary and string formats
                if isinstance(skills, dict):
                    for category, skill_list in skills.items():
                        if isinstance(skill_list, list):
                            content.append(
                                f"\\textbf{{{sanitize_latex(category)}}}: {', '.join(sanitize_latex(skill) for skill in skill_list)}"
                            )
                        else:
                            content.append(
                                f"\\textbf{{{sanitize_latex(category)}}}: {sanitize_latex(skill_list)}"
                            )
                elif isinstance(skills, str):
                    content.append(sanitize_latex(skills))

            # Work Experience
            work_experience = None
            if hasattr(resume, "work_experience") and resume.work_experience:
                work_experience = resume.work_experience
            elif (
                hasattr(resume, "content")
                and isinstance(resume.content, dict)
                and "work_experience" in resume.content
            ):
                work_experience = resume.content["work_experience"]

            if work_experience:
                content.append("\\section*{Work Experience}")
                # Handle both list and string formats
                if isinstance(work_experience, list):
                    for exp in work_experience:
                        if isinstance(exp, dict):
                            company = exp.get("company", "")
                            position = exp.get("position", "")
                            start_date = exp.get("start_date", "")
                            end_date = exp.get("end_date", "")
                            responsibilities = exp.get("responsibilities", [])

                            content.extend(
                                [
                                    f"\\textbf{{{sanitize_latex(company)}}} \\hfill {start_date} -- {end_date}",
                                    f"\\textit{{{sanitize_latex(position)}}}",
                                    "\\begin{itemize}",
                                ]
                            )

                            if isinstance(responsibilities, list):
                                for resp in responsibilities:
                                    content.append(f"\\item {sanitize_latex(resp)}")
                            elif isinstance(responsibilities, str):
                                content.append(
                                    f"\\item {sanitize_latex(responsibilities)}"
                                )

                            content.append("\\end{itemize}")
                elif isinstance(work_experience, str):
                    content.append(sanitize_latex(work_experience))

            # Education
            education = None
            if hasattr(resume, "education") and resume.education:
                education = resume.education
            elif (
                hasattr(resume, "content")
                and isinstance(resume.content, dict)
                and "education" in resume.content
            ):
                education = resume.content["education"]

            if education:
                content.append("\\section*{Education}")
                # Handle both list and string formats
                if isinstance(education, list):
                    for edu in education:
                        if isinstance(edu, dict):
                            institution = edu.get("institution", "")
                            degree = edu.get("degree", "")
                            field_of_study = edu.get("field_of_study", "")
                            start_date = edu.get("start_date", "")
                            end_date = edu.get("end_date", "")

                            content.extend(
                                [
                                    f"\\textbf{{{sanitize_latex(institution)}}} \\hfill {start_date} -- {end_date}",
                                    f"{sanitize_latex(degree)} in {sanitize_latex(field_of_study)}",
                                ]
                            )
                elif isinstance(education, str):
                    content.append(sanitize_latex(education))

            # Projects section (if available)
            projects = None
            if hasattr(resume, "projects") and resume.projects:
                projects = resume.projects
            elif (
                hasattr(resume, "content")
                and isinstance(resume.content, dict)
                and "projects" in resume.content
            ):
                projects = resume.content["projects"]

            if projects:
                content.append("\\section*{Projects}")
                if isinstance(projects, list):
                    for project in projects:
                        if isinstance(project, dict):
                            name = project.get("name", "")
                            description = project.get("description", "")
                            technologies = project.get("technologies", [])

                            content.append(f"\\textbf{{{sanitize_latex(name)}}}")
                            content.append(sanitize_latex(description))

                            if technologies and isinstance(technologies, list):
                                tech_text = ", ".join(
                                    sanitize_latex(tech) for tech in technologies
                                )
                                content.append(f"\\textit{{Technologies:}} {tech_text}")
                elif isinstance(projects, str):
                    content.append(sanitize_latex(projects))

            # Awards section (if available)
            awards = None
            if hasattr(resume, "awards") and resume.awards:
                awards = resume.awards
            elif (
                hasattr(resume, "content")
                and isinstance(resume.content, dict)
                and "awards" in resume.content
            ):
                awards = resume.content["awards"]

            if awards:
                content.append("\\section*{Awards \\& Achievements}")
                if isinstance(awards, list):
                    content.append("\\begin{itemize}")
                    for award in awards:
                        if isinstance(award, dict):
                            title = award.get("title", "")
                            issuer = award.get("issuer", "")
                            date = award.get("date", "")
                            description = award.get("description", "")

                            award_text = f"\\textbf{{{sanitize_latex(title)}}}"
                            if issuer:
                                award_text += f" - {sanitize_latex(issuer)}"
                            if date:
                                award_text += f" ({date})"

                            content.append(f"\\item {award_text}")
                            if description:
                                content.append(f"{sanitize_latex(description)}")
                        else:
                            content.append(f"\\item {sanitize_latex(str(award))}")
                    content.append("\\end{itemize}")
                elif isinstance(awards, str):
                    content.append(sanitize_latex(awards))

            # Publications section (if available)
            publications = None
            if hasattr(resume, "publications") and resume.publications:
                publications = resume.publications
            elif (
                hasattr(resume, "content")
                and isinstance(resume.content, dict)
                and "publications" in resume.content
            ):
                publications = resume.content["publications"]

            if publications:
                content.append("\\section*{Publications}")
                if isinstance(publications, list):
                    for pub in publications:
                        if isinstance(pub, dict):
                            title = pub.get("title", "")
                            authors = pub.get("authors", "")
                            journal = pub.get("journal", "")
                            year = pub.get("year", "")

                            pub_text = f"\\textbf{{{sanitize_latex(title)}}}"
                            if authors:
                                pub_text += f". {sanitize_latex(authors)}"
                            if journal:
                                pub_text += f". \\textit{{{sanitize_latex(journal)}}}"
                            if year:
                                pub_text += f", {year}"

                            content.append(pub_text)
                elif isinstance(publications, str):
                    content.append(sanitize_latex(publications))

            # End document if not already included in preamble
            if "\\end{document}" not in content[-1]:
                content.append("\\end{document}")

            return "\n".join(content)

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error generating LaTeX content: {e}")
            # Print traceback for debugging
            import traceback

            logger.error(f"Traceback:\n{traceback.format_exc()}")
            # Return a basic document showing the error
            return (
                "\\documentclass{article}\\begin{document}Error generating resume: "
                + sanitize_latex(str(e))
                + "\\end{document}"
            )

    def _generate_personal_info_section(
        self, resume: Resume, template: Dict[str, Any]
    ) -> str:
        """Generate LaTeX content for the personal information section.

        Args:
            resume: Resume data
            template: LaTeX template data

        Returns:
            str: Generated LaTeX content for personal information
        """
        # Try multiple ways to access personal information
        info = {}
        try:
            # First, try direct attribute access
            if hasattr(resume, "personal_information") and resume.personal_information:
                info = resume.personal_information
            # Next, check if it's in the content dictionary
            elif (
                hasattr(resume, "content")
                and isinstance(resume.content, dict)
                and "personal_information" in resume.content
            ):
                personal_info = resume.content["personal_information"]
                # Handle if it's a JSON string
                if isinstance(personal_info, str):
                    import json

                    info = json.loads(personal_info)
                else:
                    info = personal_info
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error accessing personal information: {e}")
            # Use empty dict if all else fails
            info = {}

        # Create a consistent set of fields for placeholders
        # First try full_name, then fallback to name if available
        full_name = info.get("full_name", info.get("name", ""))

        placeholders = {
            "name": sanitize_latex(full_name),  # Keep "name" for backward compatibility
            "full_name": sanitize_latex(full_name),  # Add full_name as new standard
            "email": sanitize_latex(info.get("email", "")),
            "phone": sanitize_latex(info.get("phone", "")),
            "address": sanitize_latex(info.get("address", "")),
            "linkedin": sanitize_latex(info.get("linkedin", "")),
            "github": sanitize_latex(info.get("github", "")),
            "website": sanitize_latex(info.get("website", "")),
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
        tex_path = Path(self.output_dir) / f"{resume.id}.tex"

        # Compile to PDF
        return await self.compile_pdf(tex_path, tex_content)
