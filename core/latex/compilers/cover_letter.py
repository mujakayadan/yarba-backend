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

            # Begin document if not already in preamble
            if "\\begin{document}" not in content[-1]:
                content.append("\\begin{document}")

            # Generate personal information section
            personal_info_section = self._generate_personal_info_section(
                resume, template
            )
            content.append(personal_info_section)

            # Add current date
            content.append("\\today")
            content.append("\\vspace{1em}")

            # Get personal information in a flexible way
            personal_info = {}
            try:
                if (
                    hasattr(resume, "personal_information")
                    and resume.personal_information
                ):
                    personal_info = resume.personal_information
                elif (
                    hasattr(resume, "content")
                    and isinstance(resume.content, dict)
                    and "personal_information" in resume.content
                ):
                    personal_info_data = resume.content["personal_information"]
                    if isinstance(personal_info_data, str):
                        import json

                        personal_info = json.loads(personal_info_data)
                    else:
                        personal_info = personal_info_data
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Error accessing personal information for recipient: {e}")

            # Add recipient information if available
            if isinstance(personal_info, dict) and "recipient" in personal_info:
                recipient = personal_info["recipient"]
                if isinstance(recipient, dict):
                    content.extend(
                        [
                            sanitize_latex(recipient.get("name", "")),
                            sanitize_latex(recipient.get("title", "")),
                            sanitize_latex(recipient.get("company", "")),
                            sanitize_latex(recipient.get("address", "")),
                            "\\vspace{1em}",
                        ]
                    )

            # Get job-specific info for salutation
            company_name = ""
            job_title = ""
            hiring_manager = "Hiring Manager"

            if hasattr(resume, "company_name") and resume.company_name:
                company_name = resume.company_name
            if hasattr(resume, "job_title") and resume.job_title:
                job_title = resume.job_title

            # Try to get hiring manager name if available
            if isinstance(personal_info, dict) and "recipient" in personal_info:
                recipient = personal_info["recipient"]
                if isinstance(recipient, dict) and "name" in recipient:
                    hiring_manager = recipient["name"].split()[0]  # Use first name only

            # Add salutation with hiring manager name if available
            content.append(f"Dear {hiring_manager},")
            content.append("\\vspace{1em}")

            # Add cover letter content
            cover_letter_content = ""
            if hasattr(resume, "cover_letter_content") and resume.cover_letter_content:
                cover_letter_content = resume.cover_letter_content

            if cover_letter_content:
                paragraphs = cover_letter_content.split("\n\n")
                for paragraph in paragraphs:
                    content.append(sanitize_latex(paragraph))
                    content.append("\\vspace{1em}")

            # Get sender name for closing
            sender_name = ""
            if isinstance(personal_info, dict):
                sender_name = personal_info.get(
                    "full_name", personal_info.get("name", "")
                )

            # Add closing
            content.extend(
                [
                    "\\vspace{1em}",
                    "Sincerely,",
                    "\\vspace{2em}",
                    sanitize_latex(sender_name),
                ]
            )

            # End document if not already in template
            if "\\end{document}" not in content[-1]:
                content.append("\\end{document}")

            return "\n".join(content)

        except Exception as e:
            import logging
            import traceback

            logger = logging.getLogger(__name__)
            logger.error(f"Error generating cover letter LaTeX content: {e}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            # Return a basic document showing the error
            return (
                "\\documentclass{article}\\begin{document}Error generating cover letter: "
                + sanitize_latex(str(e))
                + "\\end{document}"
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
        try:
            # Generate LaTeX content
            tex_content = await self.generate_tex_content(resume, template)

            # Create temporary file path
            tex_path = Path(self.output_dir) / f"{resume.id}_cover_letter.tex"

            # Compile to PDF
            return await self.compile_pdf(tex_path, tex_content)
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error generating cover letter PDF: {e}")
            return None
