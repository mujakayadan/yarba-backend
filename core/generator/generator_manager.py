"""Generator manager implementation."""

from enum import Enum
from typing import Any, Dict, Optional, Tuple, Union

from ..latex.config import LatexConfig
from ..models.resume import Resume
from .combined_generator import CombinedGenerator
from .cover_letter_generator import CoverLetterGenerator
from .resume_generator import ResumeGenerator


class DocumentType(Enum):
    """Enumeration of document types that can be generated."""

    RESUME = "resume"
    COVER_LETTER = "cover_letter"
    COMBINED = "combined"


class GeneratorManager:
    """Manager class for document generation.

    This class provides a unified interface for generating different types
    of documents. It manages the different generators and handles the
    generation process based on the requested document type.
    """

    def __init__(self, config: Optional[LatexConfig] = None):
        """Initialize the generator manager.

        Args:
            config: Optional LaTeX configuration
        """
        self.config = config or LatexConfig()
        self.resume_generator = ResumeGenerator(config)
        self.cover_letter_generator = CoverLetterGenerator(config)
        self.combined_generator = CombinedGenerator(config)

    async def generate(
        self,
        doc_type: Union[DocumentType, str],
        resume: Resume,
        template: Dict[str, Any],
    ) -> Optional[Union[bytes, Tuple[bytes, bytes]]]:
        """Generate document(s) based on the requested type.

        Args:
            doc_type: Type of document to generate
            resume: Resume data
            template: Template data

        Returns:
            Optional[Union[bytes, Tuple[bytes, bytes]]]: Generated PDF content(s)
                if successful, None otherwise
        """
        # Convert string to enum if necessary
        if isinstance(doc_type, str):
            try:
                doc_type = DocumentType(doc_type.lower())
            except ValueError:
                return None

        # Generate requested document type
        if doc_type == DocumentType.RESUME:
            return await self.resume_generator.generate(resume, template)
        elif doc_type == DocumentType.COVER_LETTER:
            return await self.cover_letter_generator.generate(resume, template)
        elif doc_type == DocumentType.COMBINED:
            return await self.combined_generator.generate(resume, template)
        else:
            return None

    async def validate(
        self,
        doc_type: Union[DocumentType, str],
        resume: Resume,
        template: Dict[str, Any],
    ) -> bool:
        """Validate data for the requested document type.

        Args:
            doc_type: Type of document to validate
            resume: Resume data
            template: Template data

        Returns:
            bool: True if validation passes, False otherwise
        """
        # Convert string to enum if necessary
        if isinstance(doc_type, str):
            try:
                doc_type = DocumentType(doc_type.lower())
            except ValueError:
                return False

        # Validate for requested document type
        if doc_type == DocumentType.RESUME:
            return await self.resume_generator.validate(resume, template)
        elif doc_type == DocumentType.COVER_LETTER:
            return await self.cover_letter_generator.validate(resume, template)
        elif doc_type == DocumentType.COMBINED:
            return await self.combined_generator.validate(resume, template)
        else:
            return False
