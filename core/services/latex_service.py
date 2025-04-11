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

    def configure_latex_logging(
        self, log_level: str = None, suppress_logs: bool = None
    ):
        """
        Configure LaTeX logging settings for both compilers.

        Args:
            log_level: Log level for LaTeX compilation ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
            suppress_logs: Whether to suppress LaTeX logs in terminal output
        """
        # Only update if values are provided
        if log_level is not None:
            self.resume_compiler.log_level = log_level.upper()
            self.cover_letter_compiler.log_level = log_level.upper()
            self.logger.info(f"Set LaTeX log level to {log_level.upper()}")

        if suppress_logs is not None:
            self.resume_compiler.suppress_logs = suppress_logs
            self.cover_letter_compiler.suppress_logs = suppress_logs
            self.logger.info(f"Set LaTeX log suppression to {suppress_logs}")

    def get_current_latex_settings(self) -> dict:
        """
        Get current LaTeX compiler settings.

        Returns:
            dict: Current LaTeX compiler settings
        """
        return {
            "log_level": self.resume_compiler.log_level,
            "suppress_logs": self.resume_compiler.suppress_logs,
            "compiler_path": self.resume_compiler.compiler_path,
            "compiler_options": self.resume_compiler.compiler_options,
            "cleanup_temp_files": self.resume_compiler.cleanup_temp_files,
        }

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
    ) -> str:
        """
        Generate LaTeX for a resume.

        Args:
            resume: Resume model
            profile: Profile model

        Returns:
            str: LaTeX document
        """
        try:
            # Log input data IDs
            self.logger.info(f"Generating LaTeX for resume ID: {resume.id}")
            self.logger.info(f"Using profile ID: {profile.id}")

            # Get template ID - first check resume, then fallback to profile preferences
            template_id = None

            # Check if resume has template_id set
            if resume.template_id:
                template_id = resume.template_id
                self.logger.info(f"Using template ID from resume: {template_id}")
            # Otherwise check profile preferences
            elif (
                profile.preferences
                and profile.preferences.default_latex_templates
                and "default_resume_template_id"
                in profile.preferences.default_latex_templates
            ):
                template_id = profile.preferences.default_latex_templates[
                    "default_resume_template_id"
                ]
                self.logger.info(
                    f"Using template ID from profile preferences: {template_id}"
                )

            # Prepare template data with preamble
            template_data = await self._prepare_template_data(document_type="resume")

            # If template_id is available, add it to template_data
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
            compiler.cleanup_temp_files = settings.latex.cleanup_temp_files

            # Update log settings if they don't match the global settings
            if compiler.log_level != settings.latex.log_level:
                compiler.log_level = settings.latex.log_level
            if compiler.suppress_logs != settings.latex.suppress_logs:
                compiler.suppress_logs = settings.latex.suppress_logs

            # Compile to PDF
            pdf_content = await compiler.compile_pdf(tex_path, latex_content)

            if not pdf_content:
                raise InternalServerException(
                    "Failed to compile LaTeX to PDF. Check logs for details."
                )

            return pdf_content

        except Exception as e:
            self.logger.error(f"Error compiling LaTeX to PDF: {e}")
            import traceback

            self.logger.error(f"Traceback: {traceback.format_exc()}")
            raise InternalServerException(f"Failed to compile LaTeX to PDF: {str(e)}")


def get_latex_service() -> LatexService:
    """
    Get a new instance of LatexService.

    Returns:
        LatexService: A new instance of LatexService
    """
    return LatexService()
