"""Tests for security-sensitive URL matching."""

import pytest

from core.job_extractor.url_utils import job_posting_url_for_extraction
from core.services.portfolio_chat_service import PortfolioChatService
from core.utils.url import url_has_domain


@pytest.mark.parametrize(
    ("url", "domain", "expected"),
    [
        ("https://linkedin.com/jobs/1", "linkedin.com", True),
        ("https://www.linkedin.com/jobs/1", "linkedin.com", True),
        ("https://LINKEDIN.COM./jobs/1", "linkedin.com", True),
        ("https://linkedin.com.evil.example/jobs/1", "linkedin.com", False),
        ("https://notlinkedin.com/jobs/1", "linkedin.com", False),
        ("not a URL", "linkedin.com", False),
        ("https://[invalid", "linkedin.com", False),
    ],
)
def test_url_has_domain(url: str, domain: str, expected: bool) -> None:
    assert url_has_domain(url, domain) is expected


def test_workday_apply_url_is_normalized_for_trusted_domain() -> None:
    url = "https://tenant.myworkdayjobs.com/en-US/jobs/123/apply?source=test"

    assert (
        job_posting_url_for_extraction(url)
        == "https://tenant.myworkdayjobs.com/en-US/jobs/123"
    )


def test_workday_lookalike_domain_is_not_normalized() -> None:
    url = "https://myworkdayjobs.com.evil.example/jobs/123/apply"

    assert job_posting_url_for_extraction(url) == url


def test_scheduling_url_requires_an_exact_url_match() -> None:
    configured_url = "https://calendly.com/example-user/30min"

    assert PortfolioChatService._mentions_scheduling(
        f"Book here: {configured_url}.", configured_url
    )
    assert configured_url not in PortfolioChatService._normalized_response_urls(
        "Book here: https://example.com/calendly.com/example-user/30min"
    )
