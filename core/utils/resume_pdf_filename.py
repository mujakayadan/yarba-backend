"""Build safe PDF attachment filenames for generated resumes."""

import re
from datetime import UTC, datetime

_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _format_resume_field(value: str | None) -> str | None:
    """Format stored company_name/job_title values for filenames."""
    if not value or not value.strip():
        return None
    parts = value.strip().split("_")
    formatted = "_".join(word.capitalize() for word in parts if word)
    return formatted or None


def _sanitize_filename_stem(stem: str) -> str:
    stem = _INVALID_FILENAME_CHARS.sub("", stem)
    stem = re.sub(r"\s+", "_", stem.strip())
    stem = re.sub(r"_+", "_", stem).strip("_")
    return stem


def build_resume_pdf_filename(
    company_name: str | None,
    job_title: str | None,
    *,
    timestamp: datetime | None = None,
) -> str:
    """Build an attachment filename from extracted resume targeting fields.

    Examples:
        Morgan_Stanley + AI_Engineer -> Morgan_Stanley_AI_Engineer.pdf
        Morgan_Stanley only -> Morgan_Stanley_20250603_143022.pdf
        AI_Engineer only -> AI_Engineer_20250603_143022.pdf
        neither -> 20250603_143022.pdf
    """
    company = _format_resume_field(company_name)
    job = _format_resume_field(job_title)
    ts = (timestamp or datetime.now(UTC)).strftime("%Y%m%d_%H%M%S")

    if company and job:
        stem = f"{company}_{job}"
    elif company:
        stem = f"{company}_{ts}"
    elif job:
        stem = f"{job}_{ts}"
    else:
        stem = ts

    sanitized = _sanitize_filename_stem(stem)
    return f"{sanitized or ts}.pdf"
