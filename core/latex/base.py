"""Base LaTeX compiler implementation."""

import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from config.logging_config import get_logger

from .config import LatexConfig

logger = get_logger(__name__)


class LatexCompiler(ABC):
    """Abstract base class for LaTeX compilation.

    This class provides the base functionality for compiling LaTeX documents
    to PDF. It handles the compilation process, file management, and cleanup.
    """

    def __init__(self, config: Optional[LatexConfig] = None):
        """Initialize the compiler.

        Args:
            config: Optional LaTeX configuration
        """
        self.config = config or LatexConfig()

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
            # Create output directory if it doesn't exist
            tex_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content to file
            tex_path.write_text(tex_content)

            # Build command
            command = [
                self.config.compiler_path,
                *self.config.compiler_options,
                tex_path.name,
            ]

            # Run pdflatex in the output directory
            result = subprocess.run(
                command,
                cwd=tex_path.parent,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                logger.error(f"LaTeX Error Output:\n{result.stderr}")
                logger.error(f"LaTeX Standard Output:\n{result.stdout}")
                return None

            # Check if PDF was generated
            pdf_path = tex_path.with_suffix(".pdf")
            if pdf_path.exists():
                return pdf_path.read_bytes()
            else:
                logger.error("PDF file not found after compilation")
                return None

        except Exception as e:
            logger.error(f"Error during PDF compilation: {str(e)}")
            return None

        finally:
            if self.config.cleanup_temp_files:
                await self._cleanup_temp_files(tex_path)

    async def _cleanup_temp_files(self, tex_path: Path) -> None:
        """Clean up temporary LaTeX files.

        Args:
            tex_path: Path to the LaTeX file
        """
        output_dir = tex_path.parent
        for ext in self.config.temp_extensions:
            temp_file = output_dir / f"{tex_path.stem}{ext}"
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to cleanup {temp_file}: {e}")
