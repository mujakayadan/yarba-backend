"""Resume generator implementation."""

from typing import Any, Dict, Optional

from ..models.resume import Resume
from .base import BaseGenerator


class ResumeGenerator(BaseGenerator):
    """Resume generator for creating PDF resumes.

    This class handles the generation of resumes from resume data and templates.
    It validates the data against template requirements and uses the resume
    compiler to generate the final PDF.
    """

    async def validate(self, resume: Resume, template: Dict[str, Any]) -> bool:
        """Validate resume data against template requirements.

        Args:
            resume: Resume data
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

        # Check required sections based on template
        required_sections = template.get("required_sections", [])
        for section in required_sections:
            if not getattr(resume, section, None):
                return False

        return True

    async def generate(
        self, resume: Resume, template: Dict[str, Any]
    ) -> Optional[bytes]:
        """Generate a PDF resume.

        Args:
            resume: Resume data
            template: Template data

        Returns:
            Optional[bytes]: Generated PDF content if successful, None otherwise
        """
        # Validate resume data
        if not await self.validate(resume, template):
            return None

        # Generate PDF using resume compiler
        return await self.resume_compiler.generate_pdf(resume, template)
