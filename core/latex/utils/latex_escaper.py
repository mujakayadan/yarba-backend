"""LaTeX character escaping utilities."""

import re
from typing import Dict, Pattern

from config.logging_config import get_logger

logger = get_logger(__name__)

# Dictionary of LaTeX special characters and their escaped versions
LATEX_SPECIAL_CHARS: Dict[str, str] = {
    "&": "\\&",
    "%": "\\%",
    "$": "\\$",
    "#": "\\#",
    "_": "\\_",
    "{": "\\{",
    "}": "\\}",
    "~": "\\textasciitilde{}",
    "^": "\\textasciicircum{}",
    "\\": "\\textbackslash{}",
    "<": "\\textless{}",
    ">": "\\textgreater{}",
    "|": "\\textbar{}",
    '"': "\\textquotedbl{}",
    "'": "\\textquotesingle{}",
    "`": "\\textasciigrave{}",
}

# Compile regex pattern for special characters
LATEX_SPECIAL_CHARS_PATTERN: Pattern = re.compile(
    "|".join(map(re.escape, LATEX_SPECIAL_CHARS.keys()))
)


def escape_latex(text: str) -> str:
    """
    Escape special LaTeX characters in text.

    Args:
        text: Text to escape

    Returns:
        str: Text with LaTeX special characters escaped
    """
    if not text:
        return ""

    def replace_special_char(match: re.Match) -> str:
        """Replace special character with its LaTeX escaped version."""
        return LATEX_SPECIAL_CHARS[match.group()]

    return LATEX_SPECIAL_CHARS_PATTERN.sub(replace_special_char, text)
