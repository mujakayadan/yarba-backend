"""Cover letter compiler implementation."""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from ...models.cover_letter import CoverLetter
from ..base import LatexCompiler
from ..templates import DEFAULT_COVER_LETTER_PREAMBLE
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

    async def generate_tex_content(
        self, cover_letter: CoverLetter, template: Dict[str, Any]
    ) -> str:
        """Generate LaTeX content for a cover letter.

        Args:
            cover_letter: Cover letter data
            template: LaTeX template data containing personal_info, company_name, job_title, and cover_letter_content

        Returns:
            str: Generated LaTeX content
        """
        try:
            # Get personal information from template
            personal_info = template.get("personal_info", {})
            name = sanitize_latex(personal_info.get("name", ""))
            phone = sanitize_latex(personal_info.get("phone", ""))
            email = sanitize_latex(personal_info.get("email", ""))
            linkedin = sanitize_latex(personal_info.get("linkedin", "#"))
            github = sanitize_latex(personal_info.get("github", "#"))
            website = sanitize_latex(personal_info.get("website", "#"))
            address = sanitize_latex(personal_info.get("address", ""))

            # Get job information from template
            company_name = sanitize_latex(template.get("company_name", ""))
            job_title = sanitize_latex(template.get("job_title", ""))

            # Get cover letter content from template and process it
            cover_letter_content_raw = template.get("cover_letter_content", "")
            processed_content = self._process_cover_letter_content(
                cover_letter_content_raw
            )

            # Handle either string or dictionary return value
            if isinstance(processed_content, dict):
                cover_letter_content = processed_content.get("content", "")
                closing = processed_content.get("closing", "Sincerely,")
            else:
                cover_letter_content = processed_content
                closing = "Sincerely,"

            # Get signature information
            signature_path = template.get("signature_path")

            # Fix Windows paths for LaTeX (convert backslashes to forward slashes)
            if signature_path:
                signature_path = signature_path.replace("\\", "/")

            # Get the template preamble or use default
            preamble = DEFAULT_COVER_LETTER_PREAMBLE
            if template and "header" in template and "preamble" in template["header"]:
                preamble = template["header"]["preamble"]

            # Ensure graphicx package is included with proper options for external images
            if signature_path and "\\usepackage{graphicx}" in preamble:
                # Replace standard graphicx include with one that has proper options
                preamble = preamble.replace(
                    "\\usepackage{graphicx}", "\\usepackage[dvips,pdftex]{graphicx}"
                )

            # Generate the closing for the letter (including signature, name, and date)
            if signature_path:
                # Use quoted path for better handling of special characters
                closing_part = f"""
\\vspace{{0.5cm}}
{closing}

\\vspace{{0.3cm}}
\\includegraphics[width=1in]{{{signature_path}}}

\\textbf{{{name}}}

\\today
\\end{{letter}}
\\end{{document}}"""
            else:
                closing_part = f"""
\\vspace{{0.5cm}}
{closing}

\\vspace{{0.5cm}}
\\textbf{{{name}}}

\\today
\\end{{letter}}
\\end{{document}}"""

            # Replace placeholders in the cover letter
            return (
                (
                    preamble
                    + """
\\begin{document}
\\begin{letter}{{{COMPANY_NAME}} \\\\ {{JOB_TITLE}}}

\\personalInformation{{{NAME}}}{{{PHONE}}}{{{EMAIL}}}{{{LINKEDIN}}}{{{GITHUB}}}{{{WEBSITE}}}{{{ADDRESS}}}

\\vspace{0.3cm}
\\justifying  % Enable justification for the letter content

{{COVER_LETTER_CONTENT}}

"""
                    + closing_part
                )
                .replace("{{NAME}}", name)
                .replace("{{PHONE}}", phone)
                .replace("{{EMAIL}}", email)
                .replace("{{LINKEDIN}}", linkedin)
                .replace("{{GITHUB}}", github)
                .replace("{{WEBSITE}}", website)
                .replace("{{ADDRESS}}", address)
                .replace("{{COMPANY_NAME}}", company_name)
                .replace("{{JOB_TITLE}}", job_title)
                .replace("{{COVER_LETTER_CONTENT}}", cover_letter_content)
            )

        except Exception as e:
            self.logger.error(f"Error generating LaTeX content: {e}")
            raise

    def _process_cover_letter_content(self, content: str) -> str:
        """Process cover letter content from JSON format to LaTeX format.

        Args:
            content: Cover letter content, potentially in JSON format

        Returns:
            str: Processed content suitable for LaTeX
        """
        try:
            # Try to parse as JSON
            if not content:
                return ""

            # Dictionary to store extracted parts
            content_parts = {"content": "", "closing": "Sincerely,"}

            # Check if it looks like a JSON object
            if content.strip().startswith("{") and "paragraphs" in content:
                try:
                    # First try to parse as a proper JSON object
                    data = json.loads(content)
                except json.JSONDecodeError:
                    # If normal parsing fails, it might be a string representation of a Python dict
                    # This is a fallback but not ideal - normalize quotes first
                    content = content.replace('\\"', '"').replace("\\'", "'")
                    # Replace Python-style quotes with JSON-style quotes
                    content = content.replace("'", '"')
                    try:
                        data = json.loads(content)
                    except json.JSONDecodeError:
                        # If still fails, use the content as is
                        content_parts["content"] = sanitize_latex(content)
                        return content_parts

                # Process JSON data
                if isinstance(data, dict):
                    # Get the closing
                    if "closing" in data and data["closing"]:
                        content_parts["closing"] = sanitize_latex(data["closing"])

                    # If we have a full_document field, use that
                    if "full_document" in data and data["full_document"]:
                        # Extract just the main content without the closing
                        full_text = data["full_document"]
                        # This will usually already include the closing text, let's separate it

                        # The content will be everything up to the last paragraph
                        parts = full_text.split("\n\n")
                        if len(parts) > 1:
                            # Keep all but the last paragraph, as it usually contains the closing
                            content_parts["content"] = sanitize_latex(
                                "\n\n".join(parts[:-1])
                            )
                        else:
                            content_parts["content"] = sanitize_latex(full_text)

                        return content_parts

                    # Otherwise, build from paragraphs
                    if "paragraphs" in data and isinstance(data["paragraphs"], list):
                        greeting = sanitize_latex(
                            data.get("greeting", "Dear Hiring Manager,")
                        )
                        paragraphs = [sanitize_latex(p) for p in data["paragraphs"]]

                        # Build the content with proper paragraph spacing
                        content_parts["content"] = f"{greeting}\n\n" + "\n\n".join(
                            paragraphs
                        )
                        return content_parts

            # Return sanitized content if it's not JSON or if parsing failed
            content_parts["content"] = sanitize_latex(content)
            return content_parts
        except Exception as e:
            self.logger.error(f"Error processing cover letter content: {e}")
            # Return sanitized original content on error
            return {"content": sanitize_latex(content), "closing": "Sincerely,"}

    async def generate_pdf(
        self, cover_letter: CoverLetter, template: Dict[str, Any]
    ) -> Optional[bytes]:
        """Generate a PDF file from a cover letter.

        Args:
            cover_letter: Cover letter data
            template: LaTeX template data

        Returns:
            Optional[bytes]: PDF content if successful, None otherwise
        """
        try:
            # Get signature path from template
            signature_path = template.get("signature_path")
            signature_filename = None

            # Generate LaTeX content
            latex_content = await self.generate_tex_content(cover_letter, template)

            # Create a temp file for LaTeX compilation
            with tempfile.NamedTemporaryFile(suffix=".tex", delete=False) as temp_file:
                temp_path = Path(temp_file.name)

            # If signature path exists, copy the file to the same directory as the tex file
            if signature_path:
                try:
                    import shutil
                    from pathlib import Path

                    # Get the directory of the temp file
                    temp_dir = temp_path.parent

                    # Use a simple filename
                    signature_filename = "signature.png"
                    dest_path = temp_dir / signature_filename

                    # Copy the file
                    self.logger.info(
                        f"Copying signature from {signature_path} to {dest_path}"
                    )
                    shutil.copy2(signature_path, dest_path)

                    # Update the template to use the local filename
                    template["signature_path"] = signature_filename

                    # Regenerate LaTeX content with updated signature path
                    latex_content = await self.generate_tex_content(
                        cover_letter, template
                    )

                except Exception as e:
                    self.logger.error(f"Error copying signature file: {e}")
                    # Continue without signature if file copy fails

            # Compile to PDF
            pdf_content = await self.compile_pdf(temp_path, latex_content)

            return pdf_content

        except Exception as e:
            self.logger.error(f"Error generating PDF: {e}")
            return None
