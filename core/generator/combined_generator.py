"""Combined document generator implementation."""

from typing import Any, Dict, Optional, Tuple

from ..models.resume import Resume
from .base import BaseGenerator
from .cover_letter_generator import CoverLetterGenerator
from .resume_generator import ResumeGenerator


class CombinedGenerator(BaseGenerator):
    """Combined generator for creating both resume and cover letter PDFs.

    This class handles the generation of both resumes and cover letters from
    resume data and templates. It uses separate generators for each document
    type and combines their functionality.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the combined generator.

        Creates separate resume and cover letter generators.
        """
        super().__init__(*args, **kwargs)
        self.resume_generator = ResumeGenerator(*args, **kwargs)
        self.cover_letter_generator = CoverLetterGenerator(*args, **kwargs)

    async def validate(self, resume: Resume, template: Dict[str, Any]) -> bool:
        """Validate data for both resume and cover letter.

        Args:
            resume: Resume data
            template: Template data

        Returns:
            bool: True if validation passes for both documents
        """
        resume_valid = await self.resume_generator.validate(resume, template)
        cover_letter_valid = await self.cover_letter_generator.validate(
            resume, template
        )
        return resume_valid and cover_letter_valid

    async def generate(
        self, resume: Resume, template: Dict[str, Any]
    ) -> Optional[Tuple[bytes, bytes]]:
        """Generate both resume and cover letter PDFs.

        Args:
            resume: Resume data
            template: Template data

        Returns:
            Optional[Tuple[bytes, bytes]]: Tuple of (resume_pdf, cover_letter_pdf)
                if successful, None otherwise
        """
        # Validate data for both documents
        if not await self.validate(resume, template):
            return None

        # Generate both documents
        resume_pdf = await self.resume_generator.generate(resume, template)
        cover_letter_pdf = await self.cover_letter_generator.generate(resume, template)

        if resume_pdf is None or cover_letter_pdf is None:
            return None

        return resume_pdf, cover_letter_pdf
