"""Normalize job URLs before description extraction."""

from __future__ import annotations

from urllib.parse import urlparse, urlunparse


def job_posting_url_for_extraction(job_url: str) -> str:
    """Return a URL suitable for scraping the job description.

    Some ATS links (e.g. Workday) point at ``/apply`` application flows.
    Extraction needs the posting page instead.
    """
    parsed = urlparse(job_url)
    domain = parsed.netloc.lower()
    path = parsed.path.rstrip("/")

    if "myworkdayjobs.com" in domain and path.endswith("/apply"):
        path = path[: -len("/apply")]
        return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))

    return job_url
