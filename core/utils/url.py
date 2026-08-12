"""Utilities for validating URL components."""

from urllib.parse import urlparse


def url_has_domain(url: str, expected_domain: str) -> bool:
    """Return whether a URL uses the domain or one of its subdomains."""
    try:
        hostname = urlparse(url).hostname
    except ValueError:
        return False

    if hostname is None:
        return False

    hostname = hostname.rstrip(".").lower()
    expected_domain = expected_domain.rstrip(".").lower()
    return hostname == expected_domain or hostname.endswith(f".{expected_domain}")
