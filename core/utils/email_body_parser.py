"""Extract job description text from forwarded email bodies."""

import re

from bs4 import BeautifulSoup

FORWARD_MARKERS = (
    "---------- forwarded message",
    "-------- forwarded message",
    "begin forwarded message",
    "original message",
    "forwarded message",
)

MIN_JOB_DESCRIPTION_LENGTH = 100


def html_to_plain_text(html: str) -> str:
    """Convert HTML email body to plain text."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text("\n", strip=True)


def strip_forwarded_headers(text: str) -> str:
    """Remove common forwarded-email header blocks."""
    lines = text.splitlines()
    cleaned: list[str] = []
    skip_block = False

    for line in lines:
        lower = line.strip().lower()
        if any(marker in lower for marker in FORWARD_MARKERS):
            skip_block = True
            continue
        if skip_block:
            if lower.startswith(("subject:", "date:", "from:", "to:", "cc:", "sent:")):
                continue
            if not line.strip():
                skip_block = False
                continue
            skip_block = False
        cleaned.append(line)

    return "\n".join(cleaned)


def strip_quoted_lines(text: str) -> str:
    """Remove lines quoted with ``>``."""
    return "\n".join(
        line for line in text.splitlines() if not line.strip().startswith(">")
    )


def normalize_whitespace(text: str) -> str:
    """Collapse excessive blank lines."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_job_description(text: str | None, html: str | None = None) -> str:
    """Extract a job description from email plain text or HTML.

    Raises:
        ValueError: If the extracted text is too short to be a job description.
    """
    body = (text or "").strip()
    if not body and html:
        body = html_to_plain_text(html)

    body = strip_forwarded_headers(body)
    body = strip_quoted_lines(body)
    body = normalize_whitespace(body)

    if len(body) < MIN_JOB_DESCRIPTION_LENGTH:
        msg = (
            f"Could not extract a job description "
            f"(minimum {MIN_JOB_DESCRIPTION_LENGTH} characters)."
        )
        raise ValueError(msg)

    return body
