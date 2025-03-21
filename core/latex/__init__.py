"""LaTeX compilation package.

This package provides LaTeX compilation utilities for generating PDF documents
from various data sources.
"""

from .base import LatexCompiler
from .config import LatexConfig

__all__ = ["LatexCompiler", "LatexConfig"]
