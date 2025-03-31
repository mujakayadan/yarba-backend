"""Template registry for LaTeX document generation.

This module provides a registry for template preambles, allowing different
visual styles to be registered, retrieved, and managed by name.
"""

from typing import Any, Dict, List, Optional

# Template registry - stores available preamble templates
RESUME_TEMPLATES: Dict[str, Dict[str, str]] = {
    "classic": {
        "id": "classic",
        "name": "Classic Resume",
        "description": "A clean, professional resume template with traditional formatting",
        "preamble": "DEFAULT_RESUME_PREAMBLE",  # Reference to preamble in templates.py
    },
    "modern": {
        "id": "modern",
        "name": "Modern Resume",
        "description": "A modern resume template with sleek design elements",
        "preamble": "DEFAULT_RESUME_PREAMBLE",  # Would be replaced with a modern variant
    },
    "academic": {
        "id": "academic",
        "name": "Academic CV",
        "description": "Focused on academic achievements, publications and research",
        "preamble": "DEFAULT_RESUME_PREAMBLE",  # Would be replaced with an academic variant
    },
}

COVER_LETTER_TEMPLATES: Dict[str, Dict[str, str]] = {
    "standard": {
        "id": "standard",
        "name": "Standard Cover Letter",
        "description": "A professional cover letter with traditional formatting",
        "preamble": "DEFAULT_COVER_LETTER_PREAMBLE",  # Reference to preamble in templates.py
    },
    "modern": {
        "id": "modern",
        "name": "Modern Cover Letter",
        "description": "A sleek, modern cover letter design",
        "preamble": "DEFAULT_COVER_LETTER_PREAMBLE",  # Would be replaced with a modern variant
    },
}

# Default template IDs
DEFAULT_RESUME_TEMPLATE_ID = "classic"
DEFAULT_COVER_LETTER_TEMPLATE_ID = "standard"


def get_resume_template(template_id: Optional[str] = None) -> Dict[str, str]:
    """Get a resume template preamble by ID.

    Args:
        template_id: ID of the template to retrieve

    Returns:
        Template dictionary with id, name, description, preamble
    """
    if not template_id:
        template_id = DEFAULT_RESUME_TEMPLATE_ID

    return RESUME_TEMPLATES.get(
        template_id, RESUME_TEMPLATES[DEFAULT_RESUME_TEMPLATE_ID]
    )


def get_cover_letter_template(template_id: Optional[str] = None) -> Dict[str, str]:
    """Get a cover letter template preamble by ID.

    Args:
        template_id: ID of the template to retrieve

    Returns:
        Template dictionary with id, name, description, preamble
    """
    if not template_id:
        template_id = DEFAULT_COVER_LETTER_TEMPLATE_ID

    return COVER_LETTER_TEMPLATES.get(
        template_id, COVER_LETTER_TEMPLATES[DEFAULT_COVER_LETTER_TEMPLATE_ID]
    )


def list_resume_templates() -> List[Dict[str, str]]:
    """List all available resume templates.

    Returns:
        List of template dictionaries with id, name and description
    """
    return [
        {"id": t["id"], "name": t["name"], "description": t["description"]}
        for t in RESUME_TEMPLATES.values()
    ]


def list_cover_letter_templates() -> List[Dict[str, str]]:
    """List all available cover letter templates.

    Returns:
        List of template dictionaries with id, name and description
    """
    return [
        {"id": t["id"], "name": t["name"], "description": t["description"]}
        for t in COVER_LETTER_TEMPLATES.values()
    ]
