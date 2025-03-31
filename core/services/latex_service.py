"""LaTeX service for LaTeX document generation."""

from datetime import datetime
from typing import Any, Dict

from config.logging_config import get_logger
from config.settings import Settings
from core.exceptions.base import InternalServerException
from core.latex.compilers import CoverLetterCompiler, ResumeCompiler
from core.latex.templates import DEFAULT_COVER_LETTER_PREAMBLE, DEFAULT_RESUME_PREAMBLE
from core.models.cover_letter import CoverLetter
from core.models.profile import Profile
from core.models.resume import Resume

settings = Settings()
logger = get_logger(__name__)


class LatexService:
    """Simplified LaTeX service for document generation."""

    def __init__(self):
        """Initialize the service."""
        self.resume_compiler = ResumeCompiler()
        self.cover_letter_compiler = CoverLetterCompiler()
        self.logger = get_logger(__name__)

    async def _prepare_template_data(
        self, document_type: str = "resume"
    ) -> Dict[str, Any]:
        """
        Prepare template data for document generation.

        Args:
            document_type: Type of document ('resume' or 'cover_letter')

        Returns:
            Template data dictionary
        """
        # Get preamble based on document type
        preamble = (
            DEFAULT_RESUME_PREAMBLE
            if document_type == "resume"
            else DEFAULT_COVER_LETTER_PREAMBLE
        )

        # Prepare template data structure
        return {
            "header": {
                "preamble": preamble,
            },
            "section_formats": {},
        }

    async def generate_resume_latex(
        self,
        resume: Resume,
        profile: Profile,
        template_id: str = None,
    ) -> str:
        """
        Generate LaTeX for a resume.

        Args:
            resume: Resume model
            profile: Profile model
            template_id: Optional template ID to override the one in resume

        Returns:
            str: LaTeX document
        """
        try:
            # Log input data IDs
            self.logger.info(f"Generating LaTeX for resume ID: {resume.id}")
            self.logger.info(f"Using profile ID: {profile.id}")
            if template_id:
                self.logger.info(f"Using template ID: {template_id}")

            # Prepare template data with preamble
            template_data = await self._prepare_template_data(document_type="resume")

            # If template_id is provided, add it to template_data
            if template_id:
                template_data["template_id"] = template_id

            # Generate the LaTeX content using the compiler
            self.logger.info("Calling resume compiler to generate tex content")
            latex_content = await self.resume_compiler.generate_tex_content(
                resume=resume, template=template_data
            )

            self.logger.info(
                f"Successfully generated LaTeX content, length: {len(latex_content)} bytes"
            )

            return latex_content

        except Exception as e:
            self.logger.error(f"Error generating resume LaTeX: {e}")
            import traceback

            self.logger.error(f"Traceback: {traceback.format_exc()}")
            raise InternalServerException(f"Failed to generate LaTeX: {str(e)}")

    async def generate_cover_letter_latex(
        self,
        cover_letter: CoverLetter,
        profile: Profile,
    ) -> str:
        """
        Generate LaTeX for a cover letter.

        Args:
            cover_letter: Cover letter model
            profile: Profile model

        Returns:
            str: LaTeX document
        """
        try:
            self.logger.info(f"Generating LaTeX for cover letter ID: {cover_letter.id}")
            self.logger.info(f"Using profile ID: {profile.id}")

            # Get cover letter data
            cover_letter_text = cover_letter.cover_letter_content or ""
            company_name = cover_letter.company_name or ""
            job_title = cover_letter.job_title or ""

            # Prepare template data
            template_data = await self._prepare_template_data(
                document_type="cover_letter"
            )

            # Generate the LaTeX content using the compiler
            self.logger.info("Calling cover letter compiler to generate tex content")
            latex_content = await self.cover_letter_compiler.generate_tex_content(
                cover_letter, template_data
            )

            self.logger.info(
                f"Successfully generated cover letter LaTeX, length: {len(latex_content)} bytes"
            )
            return latex_content

        except Exception as e:
            self.logger.error(f"Error generating cover letter LaTeX: {e}")
            import traceback

            self.logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise InternalServerException(f"Failed to generate LaTeX: {str(e)}")

    async def compile_latex_to_pdf(
        self, latex_content: str, is_cover_letter: bool = False
    ) -> bytes:
        """
        Compile LaTeX content to PDF.

        Args:
            latex_content: LaTeX content
            is_cover_letter: Whether the content is for a cover letter

        Returns:
            bytes: PDF content

        Raises:
            InternalServerException: If compilation fails
        """
        try:
            # Create output directory
            output_dir = settings.latex.output_dir
            output_dir.mkdir(parents=True, exist_ok=True)

            # Create unique filename and temp directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            document_type = "cover_letter" if is_cover_letter else "resume"
            filename = f"{document_type}_{timestamp}"

            # Create temp directory
            temp_dir = output_dir / "temp" / timestamp
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Log configuration
            self.logger.info(f"Compiling {document_type} in {temp_dir}")

            # Save LaTeX content to files
            tex_path = temp_dir / "document.tex"
            tex_path.write_text(latex_content)

            # Use appropriate compiler
            compiler = (
                self.cover_letter_compiler if is_cover_letter else self.resume_compiler
            )

            # Configure compiler
            compiler.compiler_path = settings.latex.compiler_path
            compiler.compiler_options = settings.latex.compiler_options
            compiler.cleanup_temp_files = False  # Keep temp files for debugging
            compiler.temp_extensions = settings.latex.temp_extensions

            # Compile to PDF
            self.logger.info(
                f"Starting PDF compilation with {compiler.__class__.__name__}"
            )
            pdf_content = await compiler.compile_pdf(tex_path, latex_content)

            # Handle compilation failure
            if pdf_content is None:
                log_file = temp_dir / "document.log"
                log_content = (
                    log_file.read_text() if log_file.exists() else "Log file not found"
                )
                error_msg = f"LaTeX compilation failed for {document_type}. Check log: {log_file}"
                self.logger.error(error_msg)
                self.logger.error(f"LaTeX log: {log_content}")
                raise InternalServerException(error_msg)

            # Save PDF output for reference
            pdf_path = output_dir / f"{filename}.pdf"
            pdf_path.write_bytes(pdf_content)
            self.logger.info(
                f"Compilation successful. PDF saved to {pdf_path} ({len(pdf_content)} bytes)"
            )

            return pdf_content

        except Exception as e:
            self.logger.error(f"Error compiling LaTeX: {e}")
            import traceback

            self.logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise InternalServerException(f"Error compiling LaTeX: {str(e)}")


def get_latex_service() -> LatexService:
    """
    Get a new instance of LatexService.

    Returns:
        LatexService: A new instance of LatexService
    """
    return LatexService()
