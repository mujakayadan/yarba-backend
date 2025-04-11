"""Base LaTeX compiler implementation."""

import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


class LatexCompiler(ABC):
    """Abstract base class for LaTeX compilation.

    This class provides the base functionality for compiling LaTeX documents
    to PDF. It handles the compilation process, file management, and cleanup.
    """

    def __init__(self):
        """Initialize the compiler with settings from the application configuration."""
        # Use settings directly
        self.compiler_path = settings.latex.compiler_path
        self.output_dir = settings.latex.output_dir
        self.temp_extensions = settings.latex.temp_extensions
        self.compiler_options = settings.latex.compiler_options
        self.cleanup_temp_files = settings.latex.cleanup_temp_files
        self.templates_dir = settings.latex.templates_dir
        self.suppress_logs = settings.latex.suppress_logs
        self.log_level = settings.latex.log_level
        self.logger = logger

    @abstractmethod
    async def generate_tex_content(self, *args, **kwargs) -> str:
        """Generate LaTeX content.

        This method must be implemented by subclasses to generate
        the LaTeX content for their specific document type.

        Returns:
            str: Generated LaTeX content
        """
        pass

    async def compile_pdf(self, tex_path: Path, tex_content: str) -> Optional[bytes]:
        """Compile LaTeX content to PDF.

        Args:
            tex_path: Path to save the LaTeX file
            tex_content: LaTeX content to compile

        Returns:
            Optional[bytes]: PDF content if successful, None otherwise
        """
        try:
            # Log compilation settings
            self.logger.info(f"Starting LaTeX compilation at: {tex_path.parent}")

            # Create output directory if it doesn't exist
            tex_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content to file
            tex_path.write_text(tex_content)

            if not tex_path.exists() or tex_path.stat().st_size == 0:
                self.logger.error(f"Failed to write LaTeX content to {tex_path}")
                return None

            # Build command
            command = [
                self.compiler_path,
                *self.compiler_options,
                "-output-directory",
                str(tex_path.parent.absolute()),
                tex_path.name,
            ]

            # Log command based on log level settings
            if self.log_level == "DEBUG":
                self.logger.debug(f"Running: {' '.join(command)}")
            else:
                self.logger.info(f"Compiling LaTeX document: {tex_path.name}")

            # Run pdflatex in the output directory with appropriate settings
            # Capture output only if suppress_logs is True
            result = subprocess.run(
                command,
                cwd=tex_path.parent,
                capture_output=self.suppress_logs,
                text=True,
            )

            # Check if compilation was successful
            if result.returncode != 0:
                error_message = (
                    f"LaTeX compilation failed with code {result.returncode}"
                )
                self.logger.error(error_message)

                # Save error output to file for easier debugging
                error_log = tex_path.with_suffix(".error.log")

                # If suppress_logs is True, result.stdout and result.stderr will have the logs
                if self.suppress_logs:
                    error_log.write_text(
                        f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
                    )
                    self.logger.error(f"Saved error log to: {error_log}")

                    # Log a preview of the error based on log level
                    if self.log_level in ["DEBUG", "INFO"]:
                        # Show more detailed error info for lower log levels
                        stderr_preview = (
                            result.stderr[-500:]
                            if len(result.stderr) > 500
                            else result.stderr
                        )
                        self.logger.error(f"LaTeX error preview:\n{stderr_preview}")
                else:
                    # If logs weren't captured, at least save the error message
                    error_log.write_text(error_message)
                    self.logger.error(
                        f"Compilation failed. Check LaTeX logs in console output."
                    )

                # List the directory to see what files were created
                if self.log_level == "DEBUG":
                    self.logger.debug("Output directory contents:")
                    for file in tex_path.parent.iterdir():
                        self.logger.debug(
                            f"  {file.name} - {file.stat().st_size} bytes"
                        )

                return None

            # Check if PDF was generated
            pdf_path = tex_path.with_suffix(".pdf")
            if not pdf_path.exists():
                self.logger.error(f"PDF file not found: {pdf_path}")
                # List directory contents for debugging
                if self.log_level == "DEBUG":
                    self.logger.debug("Output directory contents:")
                    for file in tex_path.parent.iterdir():
                        self.logger.debug(
                            f"  {file.name} - {file.stat().st_size} bytes"
                        )
                return None

            # Check PDF size
            pdf_size = pdf_path.stat().st_size
            if pdf_size == 0:
                self.logger.error("PDF file is empty (0 bytes)")
                return None

            # Read and return PDF content
            pdf_content = pdf_path.read_bytes()
            self.logger.info(f"Successfully compiled PDF: {len(pdf_content)} bytes")
            return pdf_content

        except Exception as e:
            self.logger.error(f"Error during PDF compilation: {str(e)}")

            # Only show full traceback for DEBUG or INFO levels
            if self.log_level in ["DEBUG", "INFO"]:
                import traceback

                self.logger.error(f"Traceback:\n{traceback.format_exc()}")

            return None

        finally:
            if self.cleanup_temp_files:
                await self._cleanup_temp_files(tex_path)

    async def _cleanup_temp_files(self, tex_path: Path) -> None:
        """Clean up temporary LaTeX files.

        Args:
            tex_path: Path to the LaTeX file
        """
        output_dir = tex_path.parent
        for ext in self.temp_extensions:
            temp_file = output_dir / f"{tex_path.stem}{ext}"
            if temp_file.exists():
                try:
                    temp_file.unlink()
                    self.logger.debug(f"Cleaned up temporary file: {temp_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to cleanup {temp_file}: {e}")
