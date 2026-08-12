import logging
from urllib.parse import urlparse

from core.models.job_extractor import JobDetails
from core.utils.url import url_has_domain

from .extractors.crawl4ai_extractor import Crawl4AIExtractor
from .extractors.generic_extractor import GenericExtractor
from .extractors.linkedin_extractor import LinkedInExtractor
from .url_utils import job_posting_url_for_extraction

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


class ExtractorManager:
    """Manages different extractors for various job sites.
    This class is the main entry point for extracting job data from a URL.

    The extraction strategy is:
    1. LinkedIn URLs use the specialized LinkedInExtractor
    2. All other URLs primarily use GenericExtractor (optimized with domain-specific selectors)
    3. Crawl4AIExtractor serves as a fallback if GenericExtractor fails (optional)
    """

    def __init__(
        self,
        headless: bool = True,
        fast_mode: bool = False,
        use_crawl4ai_fallback: bool = False,
    ):
        """Initialize the ExtractorManager.

        Args:
            headless: Whether to run browsers in headless mode.
            fast_mode: Whether to use faster scraping settings (shorter timeouts).
            use_crawl4ai_fallback: Whether to enable Crawl4AI extractor as fallback.
        """
        self.headless = headless
        self.fast_mode = fast_mode
        self.use_crawl4ai_fallback = use_crawl4ai_fallback

        # Initialize extractors
        self.linkedin_extractor = LinkedInExtractor(headless=self.headless)
        self.generic_extractor = GenericExtractor(
            headless=self.headless, fast_mode=self.fast_mode
        )
        if self.use_crawl4ai_fallback:
            self.crawl4ai_extractor = Crawl4AIExtractor(
                headless=self.headless, fast_mode=self.fast_mode
            )

    async def extract(self, job_url: str) -> JobDetails | None:
        """Extract job description from a URL, handling different job sites.

        Args:
            job_url: URL of the job posting.

        Returns:
            JobDetails object with extracted content, or None if extraction fails.
        """
        parsed_url = urlparse(job_url)
        domain = (parsed_url.hostname or "").lower()
        extraction_url = job_posting_url_for_extraction(job_url)
        if extraction_url != job_url:
            logger.info("Normalized extraction URL: %s -> %s", job_url, extraction_url)

        logger.info(f"Received job URL: {job_url} (Domain: {domain})")

        # LinkedIn gets special handling due to its specific requirements
        if url_has_domain(job_url, "linkedin.com"):
            logger.info("LinkedIn URL detected. Using LinkedInExtractor...")
            result = await self.linkedin_extractor.scrape_job_posting(job_url)
            if result and result.description:
                return result
            logger.warning(
                "LinkedInExtractor failed for %s; trying GenericExtractor fallback...",
                job_url,
            )

        # For all other domains, use GenericExtractor as the primary extractor
        logger.info(
            f"Using GenericExtractor as primary extractor for domain: {domain}..."
        )
        try:
            result = await self.generic_extractor.scrape_job_posting(extraction_url)
            if result:
                logger.info(f"GenericExtractor successfully extracted from {domain}")
                return result
            else:
                logger.warning(f"GenericExtractor failed for {domain}")

        except Exception as e:
            logger.error(f"GenericExtractor error for {domain}: {e}")

        # Optional fallback to Crawl4AI if enabled and GenericExtractor fails
        if self.use_crawl4ai_fallback:
            logger.info(f"Using Crawl4AIExtractor as fallback for domain: {domain}...")
            try:
                result = await self.crawl4ai_extractor.scrape_job_posting(
                    extraction_url
                )
                if result:
                    logger.info(
                        f"Crawl4AIExtractor successfully extracted from {domain} as fallback"
                    )
                    return result
                else:
                    logger.warning(
                        f"Crawl4AIExtractor fallback also failed for {domain}"
                    )

            except Exception as e:
                logger.error(f"Crawl4AIExtractor fallback error for {domain}: {e}")

        logger.error(f"All extraction methods failed for {domain}")
        return None
