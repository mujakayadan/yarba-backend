"""Resume compiler implementation."""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...models.resume import Resume
from ..base import LatexCompiler
from ..processors import get_processor_for_section
from ..templates import DEFAULT_RESUME_PREAMBLE
from ..utils.safety import sanitize_latex


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

    def _get_section_data(self, resume: Resume, section_name: str) -> Optional[Any]:
        """
        Get data for a specific section from the resume.

        Args:
            resume: Resume model
            section_name: Name of the section

        Returns:
            Section data if found, None otherwise
        """
        # Try to get data from content dictionary
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

        return section_data

    async def generate_tex_content(
        self, resume: Resume, template: Dict[str, Any]
    ) -> str:
        """Generate LaTeX content for a resume.

        Args:
            resume: Resume data
            template: LaTeX template data (can be empty, we'll use hardcoded templates)

        Returns:
            str: Generated LaTeX content
        """
        try:
            # Check for template_id in the template dictionary
            template_id = None
            if template and "template_id" in template:
                template_id = template["template_id"]
                self.logger.info(f"Using template_id from template data: {template_id}")

            # Initialize document structure
            document_parts = []

            # Define sections to process in order
            sections = [
                "personal_information",
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
                # Get section data
                section_data = self._get_section_data(resume, section_name)

                # Skip if no data
                if not section_data:
                    self.logger.debug(f"No data for section {section_name}, skipping")
                    continue

                try:
                    # Get the processor for this section
                    section_processor = get_processor_for_section(section_name)()

                    # Process the section content - each processor now returns fully formatted LaTeX
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

                    # Add the processed content directly to the document parts
                    document_parts.append(processed_content)
                    self.logger.debug(f"Added {section_name} section")

                except Exception as e:
                    self.logger.error(f"Error processing {section_name}: {e}")
                    self.logger.error(f"Section data: {str(section_data)[:100]}")

            # Use preamble from template if provided, otherwise use default
            preamble = DEFAULT_RESUME_PREAMBLE
            if template and "header" in template and "preamble" in template["header"]:
                preamble = template["header"]["preamble"]

            # Format the complete document
            latex_content = preamble + "\n"
            latex_content += "\\begin{document}\n\n"
            latex_content += "".join(document_parts)
            latex_content += "\\end{document}"

            return latex_content

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
