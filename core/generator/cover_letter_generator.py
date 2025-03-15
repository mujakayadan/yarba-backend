"""Cover letter generator implementation."""

from typing import Any, Dict, Optional

from ..models.resume import Resume
from .base import BaseGenerator


class CoverLetterGenerator(BaseGenerator):
    """Cover letter generator for creating PDF cover letters.

    This class handles the generation of cover letters from resume data and templates.
    It validates the data against template requirements and uses the cover letter
    compiler to generate the final PDF.
    """

    async def validate(self, resume: Resume, template: Dict[str, Any]) -> bool:
        """Validate cover letter data against template requirements.

        Args:
            resume: Resume data (containing cover letter content)
            template: Template data

        Returns:
            bool: True if validation passes, False otherwise
        """
        # Check required personal information
        required_personal_info = {"name", "email", "phone", "address", "linkedin"}
        if not all(
            key in resume.personal_information for key in required_personal_info
        ):
            return False

        # Check for cover letter content
        if not resume.cover_letter_content:
            return False

        # Check recipient information if required by template
        if template.get("require_recipient", False):
            if "recipient" not in resume.personal_information:
                return False
            required_recipient_info = {"name", "title", "company", "address"}
            recipient = resume.personal_information.get("recipient", {})
            if not all(key in recipient for key in required_recipient_info):
                return False

        return True

    async def generate(
        self, resume: Resume, template: Dict[str, Any]
    ) -> Optional[bytes]:
        """Generate a PDF cover letter.

        Args:
            resume: Resume data (containing cover letter content)
            template: Template data

        Returns:
            Optional[bytes]: Generated PDF content if successful, None otherwise
        """
        # Validate cover letter data
        if not await self.validate(resume, template):
            return None

        # Generate PDF using cover letter compiler
        return await self.cover_letter_compiler.generate_pdf(resume, template)
