"""Generator manager for coordinating document generation."""

from typing import Any, Dict, List, Optional, Tuple, Union

from config.logging_config import get_logger
from config.settings import Settings
from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.models.resume import Resume

from .base import BaseGenerator
from .combined_generator import CombinedGenerator
from .cover_letter_generator import CoverLetterGenerator
from .resume_generator import ResumeGenerator

logger = get_logger(__name__)


class GeneratorManager:
    """Manager for coordinating document generation.

    This class provides a unified interface for generating different types of
    documents, including resumes and cover letters. It handles the selection
    of appropriate generators and manages the generation process.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the generator manager.

        Args:
            settings: Application settings
        """
        self.settings = settings or Settings()
        self.logger = logger

    async def generate_resume(
        self,
        profile: Profile,
        resume: Resume,
        portfolio: Optional[Portfolio] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate a resume.

        Args:
            profile: User profile
            resume: Resume to generate
            portfolio: Optional portfolio data
            **kwargs: Additional arguments for generation

        Returns:
            Dict[str, Any]: Generated resume content
        """
        generator = ResumeGenerator(
            profile=profile,
            portfolio=portfolio,
            resume=resume,
            settings=self.settings,
        )

        return await generator.generate(**kwargs)

    async def generate_cover_letter(
        self,
        profile: Profile,
        resume: Resume,
        portfolio: Optional[Portfolio] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate a cover letter.

        Args:
            profile: User profile
            resume: Resume to generate cover letter for
            portfolio: Optional portfolio data
            **kwargs: Additional arguments for generation

        Returns:
            Dict[str, Any]: Generated cover letter content
        """
        generator = CoverLetterGenerator(
            profile=profile,
            portfolio=portfolio,
            resume=resume,
            settings=self.settings,
        )

        return await generator.generate(**kwargs)

    async def generate_combined(
        self,
        profile: Profile,
        resume: Resume,
        portfolio: Optional[Portfolio] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate both resume and cover letter.

        Args:
            profile: User profile
            resume: Resume to generate
            portfolio: Optional portfolio data
            **kwargs: Additional arguments for generation

        Returns:
            Dict[str, Any]: Generated content with both resume and cover letter
        """
        generator = CombinedGenerator(
            profile=profile,
            portfolio=portfolio,
            resume=resume,
            settings=self.settings,
        )

        return await generator.generate(**kwargs)

    async def generate_by_type(
        self,
        generator_type: str,
        profile: Profile,
        resume: Resume,
        portfolio: Optional[Portfolio] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate content based on generator type.

        Args:
            generator_type: Type of generator to use ("resume", "cover_letter", or "combined")
            profile: User profile
            resume: Resume to generate
            portfolio: Optional portfolio data
            **kwargs: Additional arguments for generation

        Returns:
            Dict[str, Any]: Generated content

        Raises:
            ValueError: If an invalid generator type is provided
        """
        if generator_type == "resume":
            return await self.generate_resume(profile, resume, portfolio, **kwargs)
        elif generator_type == "cover_letter":
            return await self.generate_cover_letter(
                profile, resume, portfolio, **kwargs
            )
        elif generator_type == "combined":
            return await self.generate_combined(profile, resume, portfolio, **kwargs)
        else:
            raise ValueError(f"Invalid generator type: {generator_type}")

    async def get_available_generators(self) -> List[Dict[str, Any]]:
        """Get a list of available generators.

        Returns:
            List[Dict[str, Any]]: List of available generators with metadata
        """
        return [
            {
                "type": "resume",
                "name": "Resume Generator",
                "description": "Generates a resume from profile and portfolio data",
            },
            {
                "type": "cover_letter",
                "name": "Cover Letter Generator",
                "description": "Generates a cover letter from profile and portfolio data",
            },
            {
                "type": "combined",
                "name": "Combined Generator",
                "description": "Generates both a resume and cover letter",
            },
        ]
