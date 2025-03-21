"""Generator manager for coordinating document generation."""

from typing import Any, Dict, List, Optional, Tuple, Union

from config.logging_config import get_logger
from config.settings import Settings
from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.models.resume import Resume
from core.repositories.preamble import PreambleRepository
from core.repositories.tex_header import TexHeaderRepository
from core.repositories.tex_template import TexTemplateRepository
from core.services.latex import Latex
from core.services.llm_service import LLMService

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

    def __init__(
        self,
        profile: Profile,
        resume: Resume,
        portfolio: Optional[Portfolio] = None,
        llm_service: Optional[LLMService] = None,
        preamble_repository: Optional[PreambleRepository] = None,
        tex_header_repository: Optional[TexHeaderRepository] = None,
        tex_template_repository: Optional[TexTemplateRepository] = None,
        latex_service: Optional[Latex] = None,
    ):
        """Initialize the generator manager.

        Args:
            profile: User profile
            resume: Resume to generate content for
            portfolio: Optional portfolio data
            llm_service: LLM service for content generation
            preamble_repository: Repository for LaTeX preambles
            tex_header_repository: Repository for LaTeX headers
            tex_template_repository: Repository for LaTeX templates
            latex_service: Service for compiling LaTeX to PDF
        """
        self.profile = profile
        self.resume = resume
        self.portfolio = portfolio
        self.llm_service = llm_service
        self.preamble_repository = preamble_repository
        self.tex_header_repository = tex_header_repository
        self.tex_template_repository = tex_template_repository
        self.latex_service = latex_service
        self.logger = get_logger(__name__).getChild("GeneratorManager")

        # Initialize generators
        self.generators = {
            "resume": ResumeGenerator(
                profile=profile,
                resume=resume,
                portfolio=portfolio,
                llm_service=llm_service,
                preamble_repository=preamble_repository,
                tex_header_repository=tex_header_repository,
                tex_template_repository=tex_template_repository,
            ),
            "cover_letter": CoverLetterGenerator(
                profile=profile,
                resume=resume,
                portfolio=portfolio,
                llm_service=llm_service,
                preamble_repository=preamble_repository,
                tex_header_repository=tex_header_repository,
                tex_template_repository=tex_template_repository,
            ),
            "combined": CombinedGenerator(
                profile=profile,
                resume=resume,
                portfolio=portfolio,
                llm_service=llm_service,
                preamble_repository=preamble_repository,
                tex_header_repository=tex_header_repository,
                tex_template_repository=tex_template_repository,
            ),
        }

    async def generate(
        self, generator_type: str = "resume", compile_pdf: bool = False, **kwargs
    ) -> Dict[str, Any]:
        """Generate document content using the specified generator.

        Args:
            generator_type: Type of generator to use ("resume", "cover_letter", or "combined")
            compile_pdf: Whether to compile the generated LaTeX to PDF
            **kwargs: Additional arguments for the generator

        Returns:
            Dict[str, Any]: Generated content
        """
        self.logger.info(
            f"Generating {generator_type} for user: {self.profile.user_id}"
        )

        if generator_type not in self.generators:
            raise ValueError(f"Unknown generator type: {generator_type}")

        # Generate content
        result = await self.generators[generator_type].generate(**kwargs)

        # Compile to PDF if requested
        if compile_pdf and self.latex_service:
            try:
                self._compile_pdf(result, generator_type)
            except Exception as e:
                self.logger.error(f"Error compiling PDF: {e}")
                if "error" not in result:
                    result["error"] = {}
                result["error"]["pdf_compilation"] = str(e)

        return result

    def _compile_pdf(self, result: Dict[str, Any], generator_type: str) -> None:
        """Compile LaTeX content to PDF.

        Args:
            result: Generated content
            generator_type: Type of generator used
        """
        if not self.latex_service:
            self.logger.warning("LaTeX service not available for PDF compilation")
            return

        # Update resume with generated content
        if generator_type in ["resume", "combined"]:
            if "resume" in result and "latex_content" in result.get("resume", {}):
                latex_content = result["resume"]["latex_content"]
                pdf_path = self.latex_service.compile_latex_to_pdf(
                    latex_content, self.resume.id, is_cover_letter=False
                )
                if pdf_path:
                    result["resume"]["pdf_path"] = pdf_path
                    # Update resume with PDF path
                    self.resume.resume_pdf_path = pdf_path

        # Update cover letter with generated content
        if generator_type in ["cover_letter", "combined"]:
            if "cover_letter" in result and "latex_content" in result.get(
                "cover_letter", {}
            ):
                latex_content = result["cover_letter"]["latex_content"]
                pdf_path = self.latex_service.compile_latex_to_pdf(
                    latex_content, self.resume.id, is_cover_letter=True
                )
                if pdf_path:
                    result["cover_letter"]["pdf_path"] = pdf_path
                    # Update resume with PDF path
                    self.resume.cover_letter_pdf_path = pdf_path

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
