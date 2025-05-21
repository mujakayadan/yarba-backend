"""LaTeX module for resume and cover letter generation.

This module provides the core LaTeX functionality for the application,
including compilers, processors, and utilities for LaTeX document generation.
"""

from .base import LatexCompiler
from .compilers import CoverLetterCompiler, ResumeCompiler
from .processors import SectionProcessor, get_processor_for_section
from .utils import (
    PlaceholderManager,
    escape_latex,
    escape_latex_brackets,
    sanitize_latex,
    sanitize_latex_paragraph,
    strip_latex_commands,
)

__all__ = [
    "LatexCompiler",
    "ResumeCompiler",
    "CoverLetterCompiler",
    "SectionProcessor",
    "get_processor_for_section",
    "PlaceholderManager",
    "escape_latex",
    "escape_latex_brackets",
    "sanitize_latex",
    "sanitize_latex_paragraph",
    "strip_latex_commands",
]
