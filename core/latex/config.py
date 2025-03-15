"""LaTeX configuration."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class LatexConfig:
    """Configuration for LaTeX compilation.

    This class holds configuration options for LaTeX compilation,
    including output directory, compiler settings, and cleanup options.

    Attributes:
        output_dir: Directory for output files
        compiler_path: Path to the LaTeX compiler
        temp_extensions: Extensions of temporary files to clean up
        compiler_options: Command line options for the compiler
        cleanup_temp_files: Whether to clean up temporary files
    """

    output_dir: Path = Path("output")
    compiler_path: str = "pdflatex"
    temp_extensions: List[str] = field(default_factory=lambda: [".aux", ".log", ".out"])
    compiler_options: List[str] = field(
        default_factory=lambda: ["-interaction=nonstopmode"]
    )
    cleanup_temp_files: bool = True
