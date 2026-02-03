"""Template registry for LaTeX document generation.

This module provides a registry for template preambles, allowing different
visual styles to be registered, retrieved, and managed by name.

Templates are loaded from .tex files in the templates/latex directory and
cached in memory for performance (load once, use many times).
"""

from pathlib import Path
from typing import Dict, List, Optional

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)

# Template metadata (descriptions, names)
RESUME_TEMPLATE_METADATA: Dict[str, Dict[str, str]] = {
    "classic": {
        "id": "classic",
        "name": "Classic Resume",
        "description": "A clean, professional resume template with traditional formatting",
        "file": "resume/classic.tex",
    },
    "modern": {
        "id": "modern",
        "name": "Modern Resume",
        "description": "A modern resume template with professional colors and enhanced design",
        "file": "resume/modern.tex",
    },
    "academic": {
        "id": "academic",
        "name": "Academic CV",
        "description": "Focused on academic achievements, publications and research",
        "file": "resume/academic.tex",
    },
}

COVER_LETTER_TEMPLATE_METADATA: Dict[str, Dict[str, str]] = {
    "standard": {
        "id": "standard",
        "name": "Standard Cover Letter",
        "description": "A professional cover letter with traditional formatting",
        "file": "cover_letter/standard.tex",
    },
    "modern": {
        "id": "modern",
        "name": "Modern Cover Letter",
        "description": "A sleek, modern cover letter design",
        "file": "cover_letter/modern.tex",
    },
}

# Default template IDs
DEFAULT_RESUME_TEMPLATE_ID = "classic"
DEFAULT_COVER_LETTER_TEMPLATE_ID = "standard"

# Template cache - loaded once, reused forever
_template_cache: Dict[str, str] = {}


def _get_templates_dir() -> Path:
    """Get the templates directory path."""
    return settings.latex.templates_dir


def _load_template(file_path: str) -> str:
    """Load a template file from disk with caching.

    Args:
        file_path: Relative path to template file from templates_dir

    Returns:
        Template content as string
    """
    if file_path in _template_cache:
        return _template_cache[file_path]

    full_path = _get_templates_dir() / file_path

    if not full_path.exists():
        logger.error(f"Template file not found: {full_path}")
        raise FileNotFoundError(f"Template file not found: {full_path}")

    content = full_path.read_text(encoding="utf-8")
    _template_cache[file_path] = content
    logger.debug(f"Loaded and cached template: {file_path}")

    return content


def get_resume_template(template_id: Optional[str] = None) -> Dict[str, str]:
    """Get a resume template preamble by ID.

    Args:
        template_id: ID of the template to retrieve

    Returns:
        Template dictionary with id, name, description, preamble
    """
    if not template_id:
        template_id = DEFAULT_RESUME_TEMPLATE_ID

    metadata = RESUME_TEMPLATE_METADATA.get(
        template_id, RESUME_TEMPLATE_METADATA[DEFAULT_RESUME_TEMPLATE_ID]
    )

    preamble = _load_template(metadata["file"])

    return {
        "id": metadata["id"],
        "name": metadata["name"],
        "description": metadata["description"],
        "preamble": preamble,
    }


def get_cover_letter_template(template_id: Optional[str] = None) -> Dict[str, str]:
    """Get a cover letter template preamble by ID.

    Args:
        template_id: ID of the template to retrieve

    Returns:
        Template dictionary with id, name, description, preamble
    """
    if not template_id:
        template_id = DEFAULT_COVER_LETTER_TEMPLATE_ID

    metadata = COVER_LETTER_TEMPLATE_METADATA.get(
        template_id, COVER_LETTER_TEMPLATE_METADATA[DEFAULT_COVER_LETTER_TEMPLATE_ID]
    )

    preamble = _load_template(metadata["file"])

    return {
        "id": metadata["id"],
        "name": metadata["name"],
        "description": metadata["description"],
        "preamble": preamble,
    }


def list_resume_templates() -> List[Dict[str, str]]:
    """List all available resume templates.

    Returns:
        List of template dictionaries with id, name and description
    """
    return [
        {"id": t["id"], "name": t["name"], "description": t["description"]}
        for t in RESUME_TEMPLATE_METADATA.values()
    ]


def list_cover_letter_templates() -> List[Dict[str, str]]:
    """List all available cover letter templates.

    Returns:
        List of template dictionaries with id, name and description
    """
    return [
        {"id": t["id"], "name": t["name"], "description": t["description"]}
        for t in COVER_LETTER_TEMPLATE_METADATA.values()
    ]


def clear_template_cache() -> None:
    """Clear the template cache. Useful for hot-reloading templates during development."""
    _template_cache.clear()
    logger.info("Template cache cleared")
