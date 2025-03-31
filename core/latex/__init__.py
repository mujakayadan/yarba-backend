"""LaTeX module for resume and cover letter generation.

This module provides the core LaTeX functionality for the application,
including compilers, processors, and utilities for LaTeX document generation.
"""

from typing import Dict, Type

from .base import LatexCompiler
from .compilers import CoverLetterCompiler, ResumeCompiler
from .processors import SectionProcessor, get_processor_for_section
from .utils import sanitize_latex

__all__ = [
    "LatexCompiler",
    "ResumeCompiler",
    "CoverLetterCompiler",
    "SectionProcessor",
    "get_processor_for_section",
    "sanitize_latex",
]
