"""Base LaTeX compiler implementation."""

import asyncio
import shutil
import subprocess
from abc import ABC, abstractmethod
from datetime import datetime
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

    async def compile_pdf(
        self, tex_path: Path, latex_content: str = None
    ) -> Optional[bytes]:
        """
        Compile the LaTeX file to PDF.

        Args:
            tex_path: Path to the LaTeX file
            latex_content: Optional LaTeX content, used for logging on errors

        Returns:
            bytes: PDF content if successful, None otherwise
        """
        self.start_compile_time = datetime.now()
        self.logger.info(f"Starting LaTeX compilation at: {tex_path.parent}")
        compilation_failed = False  # Flag to track failure

        # Check if tex_path exists
        if not tex_path.exists() and latex_content:
            self.logger.warning(
                f"LaTeX file {tex_path} does not exist, writing content"
            )
            tex_path.write_text(latex_content)
        elif not tex_path.exists():
            self.logger.error(f"LaTeX file {tex_path} does not exist")
            return None

        pdf_content = None
        try:
            # Prepare the command
            cmd = [self.compiler_path, *self.compiler_options, tex_path.name]
            self.logger.info(f"Compiling LaTeX document: {tex_path.name}")

            # Function to run the subprocess
            def run_compile():
                return subprocess.run(
                    cmd,
                    cwd=str(tex_path.parent),
                    capture_output=True,  # Always capture output for logging/checking
                    check=False,  # Don't raise exception on non-zero exit, handle manually
                    text=True,  # Decode stdout/stderr as text
                )

            # Execute the command in a separate thread to avoid blocking asyncio loop
            process_result = await asyncio.to_thread(run_compile)

            # Save logs regardless of success/failure
            if process_result.stdout:
                log_path = tex_path.parent / f"{tex_path.stem}.stdout.log"
                log_path.write_text(process_result.stdout)

            if process_result.stderr:
                log_path = tex_path.parent / f"{tex_path.stem}.stderr.log"
                log_path.write_text(process_result.stderr)

            # Check if compilation was successful - returncode 0 means success
            if process_result.returncode != 0:
                compilation_failed = True  # Mark as failed
                error_log_path = tex_path.parent / f"{tex_path.stem}.error.log"
                self.logger.error(
                    f"LaTeX compilation failed with code {process_result.returncode}"
                )

                # Save the main latex log if it exists
                latex_log_path = tex_path.with_suffix(".log")
                if latex_log_path.exists():
                    try:
                        shutil.copy(latex_log_path, error_log_path)
                        self.logger.error(f"Saved main LaTeX log to: {error_log_path}")
                    except Exception as copy_err:
                        self.logger.error(
                            f"Failed to copy latex log {latex_log_path} to {error_log_path}: {copy_err}"
                        )
                else:
                    self.logger.error(
                        f"Main LaTeX log file not found at {latex_log_path}"
                    )

                # Check if PDF was created despite the errors
                pdf_path = tex_path.with_suffix(".pdf")
                if pdf_path.exists() and pdf_path.stat().st_size > 0:
                    # PDF was created despite errors, let's continue but log a warning
                    self.logger.warning(
                        "PDF was created despite compilation errors, proceeding with non-critical errors"
                    )
                    # Proceed to read the PDF content below
                else:
                    # No PDF created, log details from stderr if available
                    stderr_summary = process_result.stderr.strip().split("\n")[
                        -5:
                    ]  # Last 5 lines
                    self.logger.error(
                        f"No PDF generated. Stderr tail: {stderr_summary}"
                    )
                    return None

            # Check if PDF was created (even if errors occurred but PDF exists)
            pdf_path = tex_path.with_suffix(".pdf")
            if not pdf_path.exists():
                compilation_failed = True  # Mark as failed if PDF doesn't exist
                self.logger.error(f"PDF file {pdf_path} was not created")
                return None

            # Read the PDF content
            pdf_content = pdf_path.read_bytes()
            self.compile_time = datetime.now() - self.start_compile_time
            self.logger.info(
                f"LaTeX compilation completed in {self.compile_time.total_seconds():.2f} seconds"
            )
            self.logger.info(f"PDF size: {len(pdf_content)} bytes")

            return pdf_content

        except Exception as e:
            compilation_failed = (
                True  # Mark as failed on any exception during compilation
            )
            self.logger.error(f"Exception during LaTeX compilation process: {e}")
            import traceback

            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None  # Return None on unexpected errors
        finally:
            # Clean up temporary files ONLY if successful AND cleanup is enabled
            if not compilation_failed and self.cleanup_temp_files:
                self.logger.info("Compilation successful, cleaning up temporary files.")
                self._cleanup_temp_files(tex_path)
            elif compilation_failed:
                self.logger.warning(
                    f"Compilation failed, temporary files preserved in: {tex_path.parent}"
                )
            elif not self.cleanup_temp_files:
                self.logger.info(
                    f"Cleanup disabled, temporary files preserved in: {tex_path.parent}"
                )

    def _cleanup_temp_files(self, tex_path: Path) -> None:
        """
        Clean up temporary files generated by LaTeX.

        Args:
            tex_path: Path to the LaTeX file
        """
        # List of extensions to clean up
        temp_extensions = [
            ".aux",
            ".log",
            ".out",
            ".toc",
            ".lof",
            ".lot",
            ".fls",
            ".fdb_latexmk",
        ]

        # Add extensions from settings
        if hasattr(self, "temp_extensions") and self.temp_extensions:
            temp_extensions.extend(self.temp_extensions)

        # Clean up
        for ext in temp_extensions:
            temp_file = tex_path.with_suffix(ext)
            if temp_file.exists():
                try:
                    temp_file.unlink()
                    self.logger.debug(f"Cleaned up temporary file: {temp_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to delete {temp_file}: {e}")

        # Don't delete the original tex file or the PDF output
