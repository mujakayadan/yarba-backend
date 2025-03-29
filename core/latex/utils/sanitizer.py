"""LaTeX content sanitization utilities."""

import re
from typing import Optional

from .latex_escaper import escape_latex

# Maximum recommended line length for LaTeX files
MAX_LATEX_LINE_LENGTH = 80


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


def strip_latex_commands(text: Optional[str]) -> str:
    """Strip LaTeX commands from text.

    Args:
        text: Text to strip LaTeX commands from

    Returns:
        str: Text with LaTeX commands removed
    """
    if text is None:
        return ""

    # Convert to string if not already
    text = str(text)

    # Remove LaTeX commands (anything starting with \ and containing letters)
    text = re.sub(r"\\[a-zA-Z]+(\{[^{}]*\})*", "", text)

    # Remove LaTeX environments
    text = re.sub(r"\\begin\{.*?\}.*?\\end\{.*?\}", "", text, flags=re.DOTALL)

    # Remove LaTeX comments
    text = re.sub(r"%.*?$", "", text, flags=re.MULTILINE)

    # Remove LaTeX brackets
    text = re.sub(r"\{|\}", "", text)

    return text.strip()


def sanitize_latex_paragraph(
    text: Optional[str], max_length: int = MAX_LATEX_LINE_LENGTH
) -> str:
    """Sanitize a paragraph of text for LaTeX and format it to have reasonable line lengths.

    Args:
        text: Text to sanitize
        max_length: Maximum line length

    Returns:
        str: Sanitized text with proper line breaks
    """
    if text is None:
        return ""

    # First sanitize the text
    sanitized = sanitize_latex(text)

    # Split into words
    words = sanitized.split()

    # Build lines of appropriate length
    lines = []
    current_line = ""

    for word in words:
        if len(current_line) + len(word) + 1 <= max_length:
            if current_line:
                current_line += " " + word
            else:
                current_line = word
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    # Join lines with LaTeX newline commands
    return " \\\\\n".join(lines)
