import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from .extractors.crawl4ai_extractor import Crawl4AIExtractor
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

    The extraction strategy is:
    1. LinkedIn URLs use the specialized LinkedInExtractor
    2. All other URLs primarily use Crawl4AIExtractor (if enabled)
    3. GenericExtractor serves as a fallback if Crawl4AI fails or is disabled
    """

    def __init__(
        self, headless: bool = True, fast_mode: bool = False, use_crawl4ai: bool = True
    ):
        """
        Initialize the ExtractorManager.

        Args:
            headless: Whether to run browsers in headless mode.
            fast_mode: Whether to use faster scraping settings (shorter timeouts).
            use_crawl4ai: Whether to enable Crawl4AI extractor as the primary extractor.
        """
        self.headless = headless
        self.fast_mode = fast_mode
        self.use_crawl4ai = use_crawl4ai

        # Initialize extractors
        self.linkedin_extractor = LinkedInExtractor(headless=self.headless)
        self.generic_extractor = GenericExtractor(
            headless=self.headless, fast_mode=self.fast_mode
        )
        if self.use_crawl4ai:
            self.crawl4ai_extractor = Crawl4AIExtractor(
                headless=self.headless, fast_mode=self.fast_mode
            )

    async def extract(self, job_url: str) -> Optional[Dict[str, Any]]:
        """
        Extract job description from a URL, handling different job sites.

        Args:
            job_url: URL of the job posting.

        Returns:
            JobDetails object with extracted content, or None if extraction fails.
        """
        parsed_url = urlparse(job_url)
        domain = parsed_url.netloc.lower()

        logger.info(f"Received job URL: {job_url} (Domain: {domain})")

        # LinkedIn gets special handling due to its specific requirements
        if "linkedin.com" in domain:
            logger.info("LinkedIn URL detected. Using LinkedInExtractor...")
            return await self.linkedin_extractor.scrape_job_posting(job_url)

        # For all other domains, use Crawl4AI as the primary extractor
        if self.use_crawl4ai:
            logger.info(
                f"Using Crawl4AIExtractor as primary extractor for domain: {domain}..."
            )
            try:
                result = await self.crawl4ai_extractor.scrape_job_posting(job_url)
                if result:
                    logger.info(
                        f"Crawl4AIExtractor successfully extracted from {domain}"
                    )
                    return result
                else:
                    logger.warning(
                        f"Crawl4AIExtractor failed for {domain}, falling back to GenericExtractor"
                    )

            except Exception as e:
                logger.error(
                    f"Crawl4AIExtractor error for {domain}: {e}, falling back to GenericExtractor"
                )

        # Fallback to GenericExtractor if Crawl4AI is disabled or fails
        logger.info(f"Using GenericExtractor as fallback for domain: {domain}...")
        try:
            result = await self.generic_extractor.scrape_job_posting(job_url)
            if result:
                logger.info(f"GenericExtractor successfully extracted from {domain}")
                return result
            else:
                logger.warning(f"GenericExtractor also failed for {domain}")
                return None

        except Exception as e:
            logger.error(f"GenericExtractor error for {domain}: {e}")
            return None
