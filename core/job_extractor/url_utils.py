"""Normalize job URLs before description extraction."""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse

from core.utils.url import url_has_domain


def job_posting_url_for_extraction(job_url: str) -> str:
    """Return a URL suitable for scraping the job description.

    Some ATS links (e.g. Workday) point at ``/apply`` application flows.
    Extraction needs the posting page instead.
    """
    parsed = urlparse(job_url)
    path = parsed.path.rstrip("/")

    if url_has_domain(job_url, "myworkdayjobs.com") and path.endswith("/apply"):
        path = path[: -len("/apply")]
        return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))

    return job_url
