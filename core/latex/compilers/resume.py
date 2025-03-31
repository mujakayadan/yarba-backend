"""Resume compiler implementation."""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from ...models.resume import Resume
from ..base import LatexCompiler
from ..processors import get_processor_for_section
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

    def _parse_content_if_string(self, content: Any) -> Any:
        """
        Parse JSON strings if they are strings and look like JSON.

        Args:
            content: The content that might be a JSON string

        Returns:
            Parsed content or original content
        """
        if isinstance(content, str) and content.strip().startswith("{"):
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                self.logger.warning(
                    f"Failed to parse content as JSON: {content[:50]}..."
                )
                return content
        return content

    def _log_data_structure(self, section_name: str, data: Any, message: str):
        """
        Log information about the structure and type of data for debugging.

        Args:
            section_name: Name of the section being processed
            data: The data to log information about
            message: Additional message for context
        """
        if data is None:
            self.logger.debug(f"{section_name} {message} data is None")
            return

        if isinstance(data, str):
            self.logger.debug(
                f"{section_name} {message} is string, length: {len(data)}, starts with: {data[:50]}..."
            )
        elif isinstance(data, dict):
            self.logger.debug(
                f"{section_name} {message} is dict with keys: {list(data.keys())}"
            )
        elif isinstance(data, list):
            self.logger.debug(
                f"{section_name} {message} is list with {len(data)} items"
            )
            if data and isinstance(data[0], list):
                self.logger.debug(
                    f"{section_name} {message} appears to be nested arrays"
                )
        else:
            self.logger.debug(f"{section_name} {message} is {type(data).__name__}")

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

            # Import repository here to avoid circular imports
            from core.repositories.tex_header_repository import (
                get_tex_header_repository,
            )

            tex_header_repo = get_tex_header_repository()

            # Process personal information section first as it's special
            personal_info = None
            if hasattr(resume, "personal_information"):
                personal_info = resume.personal_information
            elif resume.content and "personal_information" in resume.content:
                personal_info = resume.content["personal_information"]

            # Log data structure
            self._log_data_structure(
                "personal_information", personal_info, "before processing"
            )

            # Process personal info if available
            if personal_info:
                self.logger.debug("Processing personal information section")
                try:
                    # Get the processor for personal info
                    personal_info_processor = get_processor_for_section(
                        "personal_information"
                    )()

                    # Process the content
                    processed_content = personal_info_processor.process(personal_info)

                    # Log processed content
                    self._log_data_structure(
                        "personal_information", processed_content, "after processing"
                    )

                    # Get the template from the database (similar to other sections)
                    section_template = await tex_header_repo.get_by_name(
                        "personal_information"
                    )

                    # Check if template exists
                    if section_template:
                        # Use template formatting
                        content_key = "personal_information_content"
                        if content_key in section_template.content:
                            section_latex = section_template.content.format(
                                **{content_key: processed_content}
                            )
                            content.append(section_latex)
                        else:
                            # Fall back to direct content + template
                            content.append(section_template.content)
                            content.append(processed_content)

                        self.logger.debug(
                            "Added personal_information section with template"
                        )
                    else:
                        # If no template, add directly (this is the old behavior)
                        self.logger.warning(
                            "No template found for personal_information, adding content directly"
                        )
                        if processed_content:
                            content.append(processed_content)
                        else:
                            self.logger.warning(
                                "Personal information processed content is empty"
                            )
                except Exception as e:
                    self.logger.error(f"Error processing personal information: {e}")

            # Process career summary section next since it might not need a template
            career_summary = None
            if hasattr(resume, "career_summary"):
                career_summary = resume.career_summary
            elif resume.content and "career_summary" in resume.content:
                career_summary = resume.content["career_summary"]
                # Parse JSON strings if needed
                career_summary = self._parse_content_if_string(career_summary)

            # Log data structure
            self._log_data_structure(
                "career_summary", career_summary, "before processing"
            )

            # Process career summary if available
            if career_summary:
                self.logger.debug("Processing career summary section")
                try:
                    # Get the processor for career summary
                    career_summary_processor = get_processor_for_section(
                        "career_summary"
                    )()

                    # Process the content
                    processed_content = career_summary_processor.process(career_summary)

                    # Log processed content
                    self._log_data_structure(
                        "career_summary", processed_content, "after processing"
                    )

                    # Get the template from the database (similar to other sections)
                    section_template = await tex_header_repo.get_by_name(
                        "career_summary"
                    )

                    # Check if template exists
                    if section_template:
                        # Use template formatting
                        content_key = "career_summary_content"
                        if content_key in section_template.content:
                            section_latex = section_template.content.format(
                                **{content_key: processed_content}
                            )
                            content.append(section_latex)
                        else:
                            # Fall back to direct content + template
                            content.append(section_template.content)
                            content.append(processed_content)

                        self.logger.debug("Added career_summary section with template")
                    else:
                        # If no template, add directly (this is the old behavior)
                        self.logger.warning(
                            "No template found for career_summary, adding content directly"
                        )
                        content.append("\\section{Career Summary}")
                        content.append(processed_content)
                except Exception as e:
                    self.logger.error(f"Error processing career summary: {e}")

            # Define remaining sections to process in order
            sections = [
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
                # Get section data from content dictionary
                section_data = None
                if (
                    hasattr(resume, "content")
                    and isinstance(resume.content, dict)
                    and section_name in resume.content
                ):
                    section_data = resume.content[section_name]
                    # Parse JSON strings if needed
                    section_data = self._parse_content_if_string(section_data)

                # If no data in content dict, try direct attribute
                if section_data is None and hasattr(resume, section_name):
                    section_data = getattr(resume, section_name)
                    # Parse JSON strings if needed
                    section_data = self._parse_content_if_string(section_data)

                # Skip if no data
                if not section_data:
                    self.logger.debug(f"No data for section {section_name}, skipping")
                    continue

                # Log data structure
                self._log_data_structure(
                    section_name, section_data, "before processing"
                )

                # Process with template from database
                try:
                    # Get the section template from the database
                    section_template = await tex_header_repo.get_by_name(section_name)

                    if not section_template:
                        self.logger.warning(
                            f"No template found for section {section_name}, skipping"
                        )
                        continue

                    # Get the processor for this section
                    section_processor = get_processor_for_section(section_name)()

                    # Process the section content
                    processed_content = section_processor.process(section_data)

                    # Log processed content
                    self._log_data_structure(
                        section_name, processed_content, "after processing"
                    )

                    # Skip empty sections
                    if not processed_content:
                        self.logger.debug(
                            f"Section {section_name} produced empty content, skipping"
                        )
                        continue

                    # Add section title and processed content
                    # The format is typically \section{SectionName} followed by the content
                    section_title = section_name.replace("_", " ").title()

                    # Check if template contains a placeholder for content
                    content_key = f"{section_name}_content"
                    if (
                        section_template.content
                        and content_key in section_template.content
                    ):
                        # Template has placeholder, use it for formatting
                        section_latex = section_template.content.format(
                            **{content_key: processed_content}
                        )
                        content.append(section_latex)
                    else:
                        # No placeholder, just add section title and content directly
                        content.append(f"\\section{{{section_title}}}")
                        content.append(processed_content)

                    self.logger.debug(f"Added {section_name} section")
                except Exception as e:
                    self.logger.error(f"Error processing {section_name}: {e}")
                    self.logger.error(f"Section data: {str(section_data)[:100]}")

            # End document if not already included in preamble
            if "\\end{document}" not in template["header"]["preamble"]:
                content.append("\\end{document}")

            # Join all lines
            return "\n".join(content)

        except Exception as e:
            self.logger.error(f"Error generating LaTeX content: {e}")
            raise

    async def generate_pdf(
        self, resume: Resume, template: Dict[str, Any]
    ) -> Optional[bytes]:
        """
        Generate a PDF file from a resume.

        Args:
            resume: Resume data
            template: LaTeX template data

        Returns:
            Optional[bytes]: PDF content if successful, None otherwise
        """
        try:
            # Generate LaTeX content
            latex_content = await self.generate_tex_content(resume, template)

            # Create a temp file for LaTeX compilation
            with tempfile.NamedTemporaryFile(suffix=".tex", delete=False) as temp_file:
                temp_path = Path(temp_file.name)

            # Compile to PDF
            pdf_content = await self.compile_pdf(temp_path, latex_content)

            return pdf_content

        except Exception as e:
            self.logger.error(f"Error generating PDF: {e}")
            return None
