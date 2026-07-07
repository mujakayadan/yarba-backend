"""LaTeX compilers for specific document types.

This module provides specialized LaTeX compilers for different document types,
such as resumes and cover letters.
"""

from .cover_letter import CoverLetterCompiler
from .resume import ResumeCompiler

__all__ = ["ResumeCompiler", "CoverLetterCompiler"]
