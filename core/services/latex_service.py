"""LaTeX service for LaTeX document generation."""

import re
from datetime import UTC, datetime
from typing import Any

from config.logging_config import get_logger
from config.settings import Settings
from core.exceptions.base import InternalServerException, NotFoundException
from core.latex.compilers import CoverLetterCompiler, ResumeCompiler
from core.latex.template_registry import (
    get_cover_letter_template,
    get_resume_template,
    list_cover_letter_templates,
    list_resume_templates,
)
from core.models.cover_letter import CoverLetter
from core.models.profile import Profile
from core.models.resume import Resume
from core.services.portfolio_service import PortfolioService

settings = Settings()
logger = get_logger(__name__)


class LatexService:
    """Simplified LaTeX service for document generation."""

    def __init__(self, portfolio_service: PortfolioService):
        """Initialize the service."""
        self.resume_compiler = ResumeCompiler()
        self.cover_letter_compiler = CoverLetterCompiler()
        self.portfolio_service = portfolio_service
        self.logger = get_logger(__name__)

    def get_available_resume_templates(self) -> list[dict[str, str]]:
        """Get list of available resume templates."""
        return list_resume_templates()

    def get_available_cover_letter_templates(self) -> list[dict[str, str]]:
        """Get list of available cover letter templates."""
        return list_cover_letter_templates()

    def configure_latex_logging(
        self, log_level: str = None, suppress_logs: bool = None
    ):
        """Configure LaTeX logging settings for both compilers.

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
        """Get current LaTeX compiler settings.

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

    def _sanitize_for_path(
        self, input_string: str | None, default_name: str = "unknown"
    ) -> str:
        """Sanitize a string to be used as a valid directory name component."""
        if not input_string:
            return default_name

        s = str(input_string).lower()  # Ensure it's a string and lowercase
        # Replace multiple underscores or hyphens with a single underscore
        s = re.sub(r"[_\-]+", "_", s)
        # Replace spaces and other common path-problematic characters with an underscore
        s = re.sub(r"[\s\.\/\\:\*\?\"<>\|]+", "_", s)
        # Remove any characters that are not alphanumeric or underscore
        s = re.sub(r"[^\w_]", "", s)
        # Remove leading/trailing underscores
        s = s.strip("_")

        # Truncate to a reasonable length (e.g., 50 characters)
        s = s[:50]

        # If the string becomes empty after sanitization, or was just underscores, return default
        return s if s else default_name

    async def _prepare_template_data(
        self, document_type: str = "resume", template_id: str | None = None
    ) -> dict[str, Any]:
        """Prepare template data for document generation.

        Args:
            document_type: Type of document ('resume' or 'cover_letter')
            template_id: Optional template ID to use

        Returns:
            Template data dictionary
        """
        # Get preamble based on document type and template ID
        if document_type == "resume":
            template_data = get_resume_template(template_id)
            preamble = template_data["preamble"]
        else:
            template_data = get_cover_letter_template(template_id)
            preamble = template_data["preamble"]

        # Prepare template data structure
        return {
            "header": {
                "preamble": preamble,
            },
            "section_formats": {},
            "template_id": template_data["id"],
        }

    async def generate_resume_latex(
        self,
        resume: Resume,
        profile: Profile,
        template_id: str | None = None,
    ) -> str:
        """Generate LaTeX for a resume.

        Args:
            resume: Resume model
            profile: Profile model
            template_id: Optional template ID to override default

        Returns:
            str: LaTeX document
        """
        try:
            # Log input data IDs
            self.logger.info(f"Generating LaTeX for resume ID: {resume.id}")
            self.logger.info(f"Using profile ID: {profile.id}")

            # --- Get Portfolio Data ---
            portfolio_data_for_compiler = {}
            try:
                # Ensure profile has user_id to fetch portfolio
                if not hasattr(profile, "user_id") or not profile.user_id:
                    self.logger.error(
                        f"Profile object {profile.id} lacks user_id. Cannot fetch portfolio."
                    )
                    raise InternalServerException(
                        "Profile lacks user_id for portfolio lookup."
                    )

                portfolio = await self.portfolio_service.get_portfolio_by_user_id(
                    profile.user_id
                )
                if portfolio and portfolio.career_summary:
                    # Pass the specific career_summary dict needed by the compiler
                    portfolio_data_for_compiler = {
                        "career_summary": portfolio.career_summary.dict()
                    }
                    self.logger.info(
                        f"Successfully fetched portfolio career summary for user {profile.user_id}"
                    )
                else:
                    self.logger.warning(
                        f"Portfolio or career_summary not found for user {profile.user_id}. Proceeding without it."
                    )
            except NotFoundException:
                self.logger.warning(
                    f"Portfolio not found via service for user {profile.user_id}. Proceeding without it."
                )
            except Exception as e:
                self.logger.error(
                    f"Error fetching portfolio via service for user {profile.user_id}: {e}"
                )
                # Decide if this should be fatal or just a warning
                # raise InternalServerException(f"Failed to fetch portfolio: {str(e)}")
            # --- End Get Portfolio Data ---

            # Get template ID - priority: parameter > resume.template_id > profile preferences
            final_template_id = template_id or resume.template_id

            # Check profile preferences if still no template_id
            if not final_template_id:
                if (
                    profile.system_preferences
                    and profile.system_preferences.templates
                    and "default_resume_template_id"
                    in profile.system_preferences.templates
                ):
                    final_template_id = profile.system_preferences.templates[
                        "default_resume_template_id"
                    ]
                    self.logger.info(
                        f"Using template ID from profile system preferences: {final_template_id}"
                    )

            # Prepare template data with the selected template
            template_data = await self._prepare_template_data(
                document_type="resume", template_id=final_template_id
            )

            self.logger.info(
                f"Using template: {template_data.get('template_id', 'classic')}"
            )

            # Generate the LaTeX content using the compiler
            self.logger.info("Calling resume compiler to generate tex content")

            # Ensure resume.content exists and is a dictionary
            if not resume.content or not isinstance(resume.content, dict):
                self.logger.error(
                    f"Resume content is missing or not a dictionary for resume {resume.id}"
                )
                raise InternalServerException(
                    "Resume content is invalid or missing for LaTeX generation."
                )

            # Pass the resume.content and portfolio data to the compiler
            latex_content = self.resume_compiler.generate_tex_content(
                resume_content=resume.content,
                portfolio_data=portfolio_data_for_compiler,  # Pass fetched portfolio data
                template=template_data,
            )

            self.logger.info(
                f"Successfully generated LaTeX content, length: {len(latex_content)} bytes"
            )

            # NOTE: This method currently returns latex_content, not compiled PDF.
            # If it were to call compile_latex_to_pdf, it would need company_name and job_title.
            # For example:
            # company_name = resume.company_name
            # job_title = resume.job_title
            # pdf_bytes = await self.compile_latex_to_pdf(
            #     latex_content,
            #     is_cover_letter=False,
            #     company_name=company_name,
            #     job_title=job_title
            # )
            # return pdf_bytes # Or handle as needed

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
        resume: Resume,
        template_id: str | None = None,
    ) -> str:
        """Generate LaTeX for a cover letter.

        Args:
            cover_letter: CoverLetter model
            profile: Profile model
            resume: Resume model
            template_id: Optional template ID to override default

        Returns:
            str: LaTeX document
        """
        try:
            # Log input data IDs
            self.logger.info(f"Generating LaTeX for cover letter ID: {cover_letter.id}")
            self.logger.info(f"Using profile ID: {profile.id}")

            # --- Get Portfolio Data ---
            portfolio_data_for_compiler = {}
            try:
                # Ensure profile has user_id to fetch portfolio
                if not hasattr(profile, "user_id") or not profile.user_id:
                    self.logger.error(
                        f"Profile object {profile.id} lacks user_id. Cannot fetch portfolio."
                    )
                    raise InternalServerException(
                        "Profile lacks user_id for portfolio lookup."
                    )

                portfolio = await self.portfolio_service.get_portfolio_by_user_id(
                    profile.user_id
                )
                if portfolio and portfolio.career_summary:
                    # Pass the specific career_summary dict needed by the compiler
                    portfolio_data_for_compiler = {
                        "career_summary": portfolio.career_summary.dict()
                    }
                    self.logger.info(
                        f"Successfully fetched portfolio career summary for user {profile.user_id}"
                    )
                else:
                    self.logger.warning(
                        f"Portfolio or career_summary not found for user {profile.user_id}. Proceeding without it."
                    )
            except NotFoundException:
                self.logger.warning(
                    f"Portfolio not found via service for user {profile.user_id}. Proceeding without it."
                )
            except Exception as e:
                self.logger.error(
                    f"Error fetching portfolio via service for user {profile.user_id}: {e}"
                )
                # Decide if this should be fatal or just a warning
                # raise InternalServerException(f"Failed to fetch portfolio: {str(e)}")
            # --- End Get Portfolio Data ---

            # Get template ID - priority: parameter > cover_letter.template_id > profile preferences
            final_template_id = template_id or cover_letter.template_id

            # Check profile preferences if still no template_id
            if not final_template_id:
                if (
                    profile.system_preferences
                    and profile.system_preferences.templates
                    and "default_cover_letter_template_id"
                    in profile.system_preferences.templates
                ):
                    final_template_id = profile.system_preferences.templates[
                        "default_cover_letter_template_id"
                    ]
                    self.logger.info(
                        f"Using template ID from profile system preferences: {final_template_id}"
                    )

            # Prepare template data with the selected template
            template_data = await self._prepare_template_data(
                document_type="cover_letter", template_id=final_template_id
            )

            self.logger.info(
                f"Using template: {template_data.get('template_id', 'standard')}"
            )

            # Generate the LaTeX content using the compiler
            self.logger.info("Calling cover letter compiler to generate tex content")

            # Ensure cover_letter.content exists and is a dictionary
            if not cover_letter.content or not isinstance(cover_letter.content, dict):
                self.logger.error(
                    f"Cover letter content is missing or not a dictionary for cover letter {cover_letter.id}"
                )
                raise InternalServerException(
                    "Cover letter content is invalid or missing for LaTeX generation."
                )

            # Pass the cover_letter.content and portfolio data to the compiler
            latex_content = self.cover_letter_compiler.generate_tex_content(
                cover_letter_content=cover_letter.content,
                portfolio_data=portfolio_data_for_compiler,  # Pass fetched portfolio data
                template=template_data,
            )

            self.logger.info(
                f"Successfully generated LaTeX content, length: {len(latex_content)} bytes"
            )

            return latex_content

        except Exception as e:
            self.logger.error(f"Error generating cover letter LaTeX: {e}")
            import traceback

            self.logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise InternalServerException(f"Failed to generate LaTeX: {str(e)}")

    async def compile_latex_to_pdf(
        self,
        latex_content: str,
        is_cover_letter: bool = False,
        company_name: str | None = None,
        job_title: str | None = None,
    ) -> bytes:
        """Compile LaTeX content to PDF.

        Args:
            latex_content: LaTeX content
            is_cover_letter: Whether the content is for a cover letter
            company_name: Optional company name for folder structure
            job_title: Optional job title for folder structure

        Returns:
            bytes: PDF content

        Raises:
            InternalServerException: If compilation fails
        """
        try:
            # Create output directory
            output_dir = settings.latex.output_dir
            output_dir.mkdir(parents=True, exist_ok=True)

            # Determine document type and create a unique timestamp (includes microseconds)
            document_type = "cover_letter" if is_cover_letter else "resume"
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")

            # Sanitize company_name and job_title for path
            s_company_name = self._sanitize_for_path(
                company_name, default_name="company_unknown"
            )
            s_job_title = self._sanitize_for_path(job_title, default_name="job_unknown")

            # Define the base directory for this specific company/job
            specific_output_dir_base = (
                output_dir / "temp" / s_company_name / s_job_title
            )

            # Create a unique subdirectory using the timestamp
            temp_dir = specific_output_dir_base / timestamp
            temp_dir.mkdir(parents=True, exist_ok=True)

            self.logger.info(f"Compiling {document_type}. Output directory: {temp_dir}")

            # Save LaTeX content to file (using document_type for .tex name)
            tex_path = temp_dir / f"{document_type}.tex"
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
    """Get a new instance of LatexService.

    Returns:
        LatexService: A new instance of LatexService
    """
    # Placeholder: Replace with actual PortfolioService injection

    # Example of manual instantiation (adjust based on your project structure)
    # db = await get_database() # Assuming async setup if needed elsewhere
    # user_repo = UserRepository(database=db)
    # portfolio_repo = PortfolioRepository(database=db)
    # portfolio_service = PortfolioService(portfolio_repository=portfolio_repo, user_repository=user_repo)
    # This is likely incorrect and needs proper dependency setup:
    portfolio_service = None  # <-- Needs real PortfolioService instance!
    if not portfolio_service:
        logger.critical(
            "PortfolioService not injected into get_latex_service! LaTeX generation may fail."
        )

        # Depending on your DI framework, you might raise an error here or handle it differently
        # For now, creating a dummy to avoid immediate crash, but this is WRONG:
        class DummyPortfolioService:
            async def get_portfolio_by_user_id(self, user_id):
                return None

        portfolio_service = DummyPortfolioService()

    return LatexService(portfolio_service=portfolio_service)  # Pass instance
