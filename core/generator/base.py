"""Base generator implementation."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ..latex.compilers import CoverLetterCompiler, ResumeCompiler
from ..latex.config import LatexConfig
from ..models.resume import Resume


class BaseGenerator(ABC):
    """Abstract base class for document generators.

    This class provides the base functionality for generating resumes and
    cover letters. It handles template management and LaTeX compilation.
    """

    def __init__(self, config: Optional[LatexConfig] = None):
        """Initialize the generator.

        Args:
            config: Optional LaTeX configuration
        """
        self.config = config or LatexConfig()
        self.resume_compiler = ResumeCompiler(config)
        self.cover_letter_compiler = CoverLetterCompiler(config)

    @abstractmethod
    async def generate(
        self, resume: Resume, template: Dict[str, Any]
    ) -> Optional[bytes]:
        """Generate a document from resume data.

        Args:
            resume: Resume data
            template: Template data

        Returns:
            Optional[bytes]: Generated PDF content if successful, None otherwise
        """
        pass

    @abstractmethod
    async def validate(self, resume: Resume, template: Dict[str, Any]) -> bool:
        """Validate resume data against template requirements.

        Args:
            resume: Resume data
            template: Template data

        Returns:
            bool: True if validation passes, False otherwise
        """
        pass
