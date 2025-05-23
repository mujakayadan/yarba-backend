import logging
from typing import Any, Dict
from urllib.parse import urlparse

from .extractors.generic_extractor import GenericExtractor
from .extractors.linkedin_extractor import LinkedInExtractor

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


class ExtractorManager:
    """
    Manages different extractors for various job sites.
    This class is the main entry point for extracting job data from a URL.
    It determines the appropriate extractor based on the URL and delegates the task.
    """

    def __init__(self, headless: bool = True, fast_mode: bool = False):
        """
        Initialize the ExtractorManager.

        Args:
            headless: Whether to run browsers in headless mode.
            fast_mode: Whether to use faster scraping settings (shorter timeouts).
                       This applies primarily to the GenericExtractor.
        """
        self.headless = headless
        self.fast_mode = fast_mode
        # Initialize extractors - they can be instantiated on demand too
        self.linkedin_extractor = LinkedInExtractor(headless=self.headless)
        self.generic_extractor = GenericExtractor(
            headless=self.headless, fast_mode=self.fast_mode
        )

    async def extract(self, job_url: str) -> Dict[str, Any]:
        """
        Extract job description from a URL, handling different job sites.

        Args:
            job_url: URL of the job posting.

        Returns:
            Dictionary with job title and description, or None if extraction fails.
        """
        parsed_url = urlparse(job_url)
        domain = parsed_url.netloc.lower()

        logger.info(f"Received job URL: {job_url} (Domain: {domain})")

        # Determine which extractor to use
        if "linkedin.com" in domain:
            logger.info("LinkedIn URL detected. Using LinkedInExtractor...")
            return await self.linkedin_extractor.scrape_job_posting(job_url)
        else:
            logger.info(f"Using GenericExtractor for domain: {domain}...")
            return await self.generic_extractor.scrape_job_posting(job_url)
