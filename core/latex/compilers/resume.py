"""Resume compiler implementation."""

from pathlib import Path
from typing import Any, Dict, Optional

from ...models.resume import Resume
from ..base import LatexCompiler
from ..utils.json_to_latex import process_content_by_section
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

            # Use preamble directly since it already contains document class, packages, etc.
            if "preamble" in template["header"] and template["header"]["preamble"]:
                # Use the provided preamble
                content.append(template["header"]["preamble"])
            else:
                # Fallback to a basic preamble if none provided
                self.logger.warning(
                    "No preamble provided, using fallback basic preamble"
                )
                content.append("\\documentclass[11pt]{article}")
                content.append("\\usepackage{geometry}")
                content.append("\\usepackage{hyperref}")
                content.append("\\begin{document}")

            # Begin document if not already included in preamble
            if "\\begin{document}" not in template["header"]["preamble"]:
                content.append("\\begin{document}")

            # Add personal information
            content.append(self._generate_personal_info_section(resume, template))

            # Define sections to process in order
            sections = [
                "career_summary",
                "skills",
                "work_experience",
                "education",
                "projects",
                "awards",
                "publications",
                "certifications",
            ]

            # Process each section
            for section_name in sections:
                section_data = None

                # Get section data from content dictionary
                if (
                    hasattr(resume, "content")
                    and isinstance(resume.content, dict)
                    and section_name in resume.content
                ):
                    section_data = resume.content[section_name]

                # If no data in content dict, try direct attribute
                if section_data is None and hasattr(resume, section_name):
                    section_data = getattr(resume, section_name)

                # Skip if still no data
                if not section_data:
                    continue

                # Add section heading
                section_title = section_name.replace("_", " ").title()
                content.append("\\section*{" + section_title + "}")

                # Convert section data to LaTeX
                try:
                    section_latex = process_content_by_section(
                        section_name, section_data
                    )
                    content.append(section_latex)
                except Exception as e:
                    self.logger.error(f"Error processing {section_name}: {e}")
                    # Fallback to simple string representation
                    content.append(sanitize_latex(str(section_data)))

            # End document if not already included in preamble
            if "\\end{document}" not in template["header"]["preamble"]:
                content.append("\\end{document}")

            # Join all lines
            return "\n".join(content)

        except Exception as e:
            self.logger.error(f"Error generating LaTeX content: {e}")
            raise

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
                personal_information = resume.content["personal_information"]
                # Handle if it's a JSON string
                if isinstance(personal_information, str):
                    import json

                    info = json.loads(personal_information)
                else:
                    info = personal_information
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
