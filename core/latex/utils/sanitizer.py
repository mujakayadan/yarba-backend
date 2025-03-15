"""LaTeX content sanitization utilities."""

import re
from typing import Optional

from .latex_escaper import escape_latex


def sanitize_latex(text: Optional[str], allow_math: bool = False) -> str:
    """Sanitize text for safe use in LaTeX documents.

    This function performs the following:
    1. Handles None values
    2. Escapes special LaTeX characters
    3. Optionally preserves math mode content
    4. Removes potentially harmful commands

    Args:
        text: Text to sanitize
        allow_math: Whether to preserve math mode content

    Returns:
        str: Sanitized text safe for LaTeX
    """
    if text is None:
        return ""

    # Convert to string if not already
    text = str(text)

    if not allow_math:
        # Remove all math mode content
        text = re.sub(r"\$.*?\$", "", text)
        text = re.sub(
            r"\\begin\{(equation|align|math).*?\}.*?\\end\{\1\}",
            "",
            text,
            flags=re.DOTALL,
        )

    # Remove potentially harmful commands
    harmful_commands = [
        r"\\input",
        r"\\include",
        r"\\write",
        r"\\read",
        r"\\openin",
        r"\\openout",
        r"\\catcode",
        r"\\def",
        r"\\let",
        r"\\futurelet",
        r"\\newcommand",
        r"\\renewcommand",
        r"\\newenvironment",
        r"\\renewenvironment",
    ]

    for command in harmful_commands:
        text = re.sub(f"{command}.*", "", text)

    # Escape special characters
    text = escape_latex(text)

    return text
