import json

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

import config.logging_config as logging_config
from core.models.job_extractor import JobDetails

from .base_extractor import BaseExtractor
from .domain_selectors import (
    get_selectors_for_url,
    get_timeout_for_url,
    requires_iframe_handling,
    should_wait_for_network_idle,
)

logger = logging_config.get_logger(__name__)


class Crawl4AIExtractor(BaseExtractor):
    """Job description extractor using Crawl4AI with comprehensive CSS selectors.

    This extractor focuses specifically on extracting job descriptions from job
    posting pages across various job boards and company career pages. It uses
    extensive CSS selectors to work with most common job posting layouts.
    """

    def __init__(self, headless: bool = True, fast_mode: bool = True):
        """Initialize the Crawl4AI job description extractor.

        Args:
            headless: Whether to run the browser in headless mode.
            fast_mode: Whether to use faster scraping with shorter timeouts.
        """
        super().__init__(headless=headless, fast_mode=fast_mode)

        # Base timeouts - will be overridden by domain-specific configs
        if getattr(self, "fast_mode", False):
            self.base_page_timeout = 15000  # 15 seconds for page load
            self.base_extraction_timeout = 10000  # 10 seconds for extraction
        else:
            self.base_page_timeout = 20000  # 20 seconds for page load
            self.base_extraction_timeout = 15000  # 15 seconds for extraction

    def _get_job_description_schema(self, url: str) -> dict:
        """Get the JSON schema for job description extraction using domain-specific selectors.

        Args:
            url: The job posting URL to get selectors for

        Returns:
            Dictionary containing the extraction schema for Crawl4AI.
        """
        # Get domain-specific selectors for this URL
        selectors = get_selectors_for_url(url)

        return {
            "name": "Job Description Content",
            "baseSelector": "body",
            "fields": [
                {
                    "name": "job_description",
                    "selector": ", ".join(selectors),
                    "type": "html",
                    "default": "",
                }
            ],
        }

    async def _extract_job_description(self, url: str) -> str | None:
        """Extract job description content using Crawl4AI with domain-specific selectors.

        Args:
            url: The job posting URL to extract from.

        Returns:
            Extracted job description as HTML string, or None if extraction fails.
        """
        # Get domain-specific configuration
        domain_timeout_seconds = get_timeout_for_url(url)
        page_timeout = domain_timeout_seconds * 1000  # Convert to milliseconds
        should_wait_network_idle = should_wait_for_network_idle(url)
        needs_iframe_handling = requires_iframe_handling(url)

        logger.info(
            f"Crawl4AI domain config for {url}: timeout={domain_timeout_seconds}s, "
            f"network_idle={should_wait_network_idle}, iframe_handling={needs_iframe_handling}"
        )

        # Configure browser for Crawl4AI
        browser_config = BrowserConfig(
            headless=self.headless,
            verbose=True,
            browser_type="chromium",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        )

        # Get the extraction schema
        schema = self._get_job_description_schema(url)
        extraction_strategy = JsonCssExtractionStrategy(schema, verbose=True)

        # Configure wait condition based on domain
        wait_for_condition = (
            "networkidle" if should_wait_network_idle else "domcontentloaded"
        )

        # Configure delay based on whether iframe handling is needed
        delay_ms = 3000 if needs_iframe_handling else 1000

        # Configure crawler run settings
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=extraction_strategy,
            page_timeout=page_timeout,
            wait_for=wait_for_condition,
            delay_before_return_html=delay_ms,
            # Minimal JavaScript for basic functionality
            js_code=[
                # Handle cookie consent
                """
                (function() {
                    const acceptButtons = document.querySelectorAll(
                        'button[id*="accept"], button[class*="accept"], ' +
                        'button[id*="consent"], button[class*="consent"], ' +
                        '[data-cookiebanner="accept"], #onetrust-accept-btn-handler'
                    );
                    acceptButtons.forEach(btn => {
                        if (btn.offsetParent !== null) btn.click();
                    });
                })();
                """,
                # Handle "Show more" buttons
                """
                (function() {
                    const showMoreButtons = document.querySelectorAll(
                        'button[class*="show-more"], button[class*="read-more"], ' +
                        '[data-testid="show-more"]'
                    );
                    showMoreButtons.forEach(btn => {
                        if (btn.offsetParent !== null) btn.click();
                    });
                })();
                """,
            ],
        )

        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                logger.info(
                    f"Crawl4AIExtractor: Starting job description extraction for {url}"
                )

                result = await crawler.arun(url=url, config=run_config)

                if not result.success:
                    logger.error(
                        f"Crawl4AIExtractor: Failed to crawl {url}: {result.error_message}"
                    )
                    return None

                if not result.extracted_content:
                    logger.warning(
                        f"Crawl4AIExtractor: No structured content extracted from {url}"
                    )
                    return None

                # Parse the extracted JSON content
                try:
                    extracted_data = json.loads(result.extracted_content)

                    # Handle both list and single object responses
                    if isinstance(extracted_data, list) and extracted_data:
                        job_description = extracted_data[0].get("job_description", "")
                    elif isinstance(extracted_data, dict):
                        job_description = extracted_data.get("job_description", "")
                    else:
                        logger.warning(
                            f"Crawl4AIExtractor: Unexpected data format from {url}"
                        )
                        return None

                    if job_description and len(job_description.strip()) > 100:
                        logger.info(
                            f"Crawl4AIExtractor: Successfully extracted job description from {url}"
                        )
                        return str(job_description).strip()
                    else:
                        logger.warning(
                            f"Crawl4AIExtractor: Job description too short or empty from {url}"
                        )
                        return None

                except json.JSONDecodeError as e:
                    logger.error(
                        f"Crawl4AIExtractor: Failed to parse extracted JSON from {url}: {e}"
                    )
                    return None

        except Exception as e:
            logger.error(
                f"Crawl4AIExtractor: Error during crawling {url}: {e}", exc_info=True
            )
            return None

    async def scrape_job_posting(self, job_url: str) -> JobDetails | None:
        """Extract job description from a job posting URL using Crawl4AI.

        Args:
            job_url: URL of the job posting.

        Returns:
            A JobDetails Pydantic model instance containing the extracted job description,
            or None if extraction fails.
        """
        logger.info(
            f"Crawl4AIExtractor: Starting job description extraction for {job_url}"
        )

        try:
            # Extract job description using comprehensive selectors
            job_description = await self._extract_job_description(job_url)

            if not job_description:
                logger.warning(
                    f"Crawl4AIExtractor: No job description extracted from {job_url}"
                )
                return None

            # Create metadata for the extraction
            extraction_metadata = {
                "extractor": "Crawl4AIExtractor",
                "extraction_method": "comprehensive_css_selectors",
                "focus": "job_description_only",
                "url": job_url,
            }

            logger.info(
                f"Crawl4AIExtractor: Successfully extracted job description from {job_url}"
            )

            return JobDetails(
                description=job_description, extraction_metadata=extraction_metadata
            )

        except Exception as e:
            logger.error(
                f"Crawl4AIExtractor: Error extracting job description from {job_url}: {e}",
                exc_info=True,
            )
            return None
