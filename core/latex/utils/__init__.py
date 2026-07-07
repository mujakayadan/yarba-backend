"""LaTeX utility modules."""

from .json_to_latex import (
    parse_json_content,
    process_awards,
    process_career_summary,
    process_content_by_section,
    process_education,
    process_personal_information,
    process_projects,
    process_publications,
    process_skills,
    process_work_experience,
)
from .placeholder import PlaceholderManager
from .safety import (
    MAX_LATEX_LINE_LENGTH,
    escape_latex,
    escape_latex_brackets,
    latex_escape_map,
    sanitize_latex,
    sanitize_latex_paragraph,
    strip_latex_commands,
)

__all__ = [
    "escape_latex",
    "escape_latex_brackets",
    "latex_escape_map",
    "PlaceholderManager",
    "sanitize_latex",
    "strip_latex_commands",
    "sanitize_latex_paragraph",
    "MAX_LATEX_LINE_LENGTH",
    "parse_json_content",
    "process_content_by_section",
    "process_personal_information",
    "process_career_summary",
    "process_skills",
    "process_work_experience",
    "process_education",
    "process_projects",
    "process_awards",
    "process_publications",
]
