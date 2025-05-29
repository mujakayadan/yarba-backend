"""
Domain-specific CSS selectors for job extraction.

This module provides a scalable way to handle different job boards
without hardcoding selectors in the generic extractor.
"""

from typing import Dict, List, Optional
from urllib.parse import urlparse


class DomainSelectorConfig:
    """Configuration for domain-specific selectors and extraction logic."""

    def __init__(
        self,
        selectors: List[str],
        timeout_seconds: int = 10,
        wait_for_network_idle: bool = True,
        requires_javascript: bool = False,
        iframe_handling: bool = False,
    ):
        """
        Initialize domain selector configuration.

        Args:
            selectors: List of CSS selectors to try in order of priority
            timeout_seconds: Maximum time to wait for page load
            wait_for_network_idle: Whether to wait for network idle state
            requires_javascript: Whether this site requires JS execution
            iframe_handling: Whether this site uses iframes for content
        """
        self.selectors = selectors
        self.timeout_seconds = timeout_seconds
        self.wait_for_network_idle = wait_for_network_idle
        self.requires_javascript = requires_javascript
        self.iframe_handling = iframe_handling


# Domain-specific configurations
DOMAIN_CONFIGS: Dict[str, DomainSelectorConfig] = {
    # iCIMS job boards
    "icims.com": DomainSelectorConfig(
        selectors=[
            "div.iCIMS_InfoMsg.iCIMS_InfoMsg_Job div.iCIMS_Expandable_Text",  # Specific job content text
            "div.iCIMS_InfoMsg_Job div.iCIMS_Expandable_Text",  # Alternative format
            "div.iCIMS_Expandable_Text",  # Direct targeting of expandable content
            "div.iCIMS_InfoMsg.iCIMS_InfoMsg_Job",  # Fallback to job sections
            "div.iCIMS_InfoMsg_Job",  # Final fallback
        ],
        timeout_seconds=10,
        wait_for_network_idle=False,  # iCIMS uses iframes, network idle is unreliable
        requires_javascript=True,
        iframe_handling=True,
    ),
    # Lever job boards
    "lever.co": DomainSelectorConfig(
        selectors=[
            "div.content-wrapper.posting-page > div.content",
            "div[data-qa='job-description']",
            "section[data-qa='job-description']",
            ".posting-content",
        ],
        timeout_seconds=8,
        wait_for_network_idle=True,
        requires_javascript=False,
    ),
    # Greenhouse job boards
    "greenhouse.io": DomainSelectorConfig(
        selectors=[
            "div.job__description.body",
            "#job-description",
            ".job-description",
            ".content",
        ],
        timeout_seconds=8,
        wait_for_network_idle=True,
        requires_javascript=False,
    ),
    # Indeed
    "indeed.com": DomainSelectorConfig(
        selectors=[
            ".jobsearch-jobDescriptionText",
            "#jobDescription",
            "[data-testid='job-description']",
            ".jobDescriptionContent",
        ],
        timeout_seconds=10,
        wait_for_network_idle=True,
        requires_javascript=True,
    ),
    # LinkedIn Jobs
    "linkedin.com": DomainSelectorConfig(
        selectors=[
            ".jobs-description__content",
            ".show-more-less-html__markup",
            ".jobs-box__html-content",
            ".job-description",
        ],
        timeout_seconds=12,
        wait_for_network_idle=True,
        requires_javascript=True,
    ),
    # Monster
    "monster.com": DomainSelectorConfig(
        selectors=[
            ".jobDescriptionContent",
            "#JobDescription",
            ".job-description",
            ".description",
        ],
        timeout_seconds=8,
        wait_for_network_idle=True,
        requires_javascript=False,
    ),
    # Glassdoor
    "glassdoor.com": DomainSelectorConfig(
        selectors=[
            ".jobDetailText",
            "[data-test='job-description']",
            ".jobDescription",
            ".desc",
        ],
        timeout_seconds=10,
        wait_for_network_idle=True,
        requires_javascript=True,
    ),
    # ZipRecruiter
    "ziprecruiter.com": DomainSelectorConfig(
        selectors=[
            ".job-description-container",
            ".job_description",
            "#job-description",
            ".description",
        ],
        timeout_seconds=8,
        wait_for_network_idle=True,
        requires_javascript=False,
    ),
    # Dice
    "dice.com": DomainSelectorConfig(
        selectors=[".jobDescText", "#jobdescSec", ".job-description", ".description"],
        timeout_seconds=8,
        wait_for_network_idle=True,
        requires_javascript=False,
    ),
    # CareerBuilder
    "careerbuilder.com": DomainSelectorConfig(
        selectors=[
            ".jobDescriptionWrapper",
            ".job-description",
            "#job-description",
            ".description",
        ],
        timeout_seconds=8,
        wait_for_network_idle=True,
        requires_javascript=False,
    ),
    # Stack Overflow Jobs
    "stackoverflow.com": DomainSelectorConfig(
        selectors=[
            ".gtmJobDescription",
            ".job-description",
            ".content",
            ".description",
        ],
        timeout_seconds=8,
        wait_for_network_idle=True,
        requires_javascript=False,
    ),
    # Taleo (Oracle)
    "taleo.net": DomainSelectorConfig(
        selectors=[
            "div[name='cwsJobDescription']",
            ".jobDescription",
            "#job-description",
            ".description",
        ],
        timeout_seconds=10,
        wait_for_network_idle=True,
        requires_javascript=True,
    ),
}

# Generic fallback selectors (used when domain is not recognized)
GENERIC_SELECTORS = [
    "#job-description",
    "#jobDescription",
    ".job-description",
    ".jobDescription",
    ".job-desc",
    ".description",
    ".job-details",
    ".job-content",
    "[data-testid='job-description']",
    "[data-automation='jobDescription']",
    "article.job-description",
    "section.job-description",
    "div.job-description",
    "article.description",
    "section.description",
    "#content",
    "#main-content",
    "div.content",
    "div.main-content",
    "article",
    "main",
]


def get_domain_config(url: str) -> Optional[DomainSelectorConfig]:
    """
    Get domain-specific configuration for a job posting URL.

    Args:
        url: The job posting URL

    Returns:
        DomainSelectorConfig if domain is recognized, None otherwise
    """
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()

        # Remove 'www.' prefix if present
        if domain.startswith("www."):
            domain = domain[4:]

        # Check for direct domain matches
        if domain in DOMAIN_CONFIGS:
            return DOMAIN_CONFIGS[domain]

        # Check for subdomain matches (e.g., jobs-company.icims.com)
        for registered_domain, config in DOMAIN_CONFIGS.items():
            if domain.endswith("." + registered_domain):
                return config

        return None

    except Exception:
        return None


def get_selectors_for_url(url: str) -> List[str]:
    """
    Get prioritized list of CSS selectors for a URL.

    Args:
        url: The job posting URL

    Returns:
        List of CSS selectors to try, in order of priority
    """
    config = get_domain_config(url)
    if config:
        return config.selectors
    else:
        return GENERIC_SELECTORS


def get_timeout_for_url(url: str) -> int:
    """
    Get appropriate timeout for a URL in seconds.

    Args:
        url: The job posting URL

    Returns:
        Timeout in seconds
    """
    config = get_domain_config(url)
    if config:
        return config.timeout_seconds
    else:
        return 10  # Default 10 second timeout


def should_wait_for_network_idle(url: str) -> bool:
    """
    Determine if we should wait for network idle state for this URL.

    Args:
        url: The job posting URL

    Returns:
        True if should wait for network idle, False otherwise
    """
    config = get_domain_config(url)
    if config:
        return config.wait_for_network_idle
    else:
        return True  # Default to waiting for network idle


def requires_javascript(url: str) -> bool:
    """
    Determine if this URL requires JavaScript execution.

    Args:
        url: The job posting URL

    Returns:
        True if requires JavaScript, False otherwise
    """
    config = get_domain_config(url)
    if config:
        return config.requires_javascript
    else:
        return False  # Default to not requiring JavaScript


def requires_iframe_handling(url: str) -> bool:
    """
    Determine if this URL uses iframes for content.

    Args:
        url: The job posting URL

    Returns:
        True if uses iframes, False otherwise
    """
    config = get_domain_config(url)
    if config:
        return config.iframe_handling
    else:
        return False  # Default to no iframe handling
