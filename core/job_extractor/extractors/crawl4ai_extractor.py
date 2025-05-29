import json
from typing import Optional

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

import config.logging_config as logging_config
from core.models.job_extractor import JobDetails

from .base_extractor import BaseExtractor

logger = logging_config.get_logger(__name__)


class Crawl4AIExtractor(BaseExtractor):
    """
    Job description extractor using Crawl4AI with comprehensive CSS selectors.

    This extractor focuses specifically on extracting job descriptions from job
    posting pages across various job boards and company career pages. It uses
    extensive CSS selectors to work with most common job posting layouts.
    """

    def __init__(self, headless: bool = True, fast_mode: bool = True):
        """
        Initialize the Crawl4AI job description extractor.

        Args:
            headless: Whether to run the browser in headless mode.
            fast_mode: Whether to use faster scraping with shorter timeouts.
        """
        super().__init__(headless=headless, fast_mode=fast_mode)

        # Configure timeouts based on mode
        if getattr(self, "fast_mode", False):
            self.page_timeout = 30000  # 30 seconds for page load
            self.extraction_timeout = 15000  # 15 seconds for extraction
        else:
            self.page_timeout = 60000  # 60 seconds for page load
            self.extraction_timeout = 30000  # 30 seconds for extraction

    def _get_job_description_schema(self) -> dict:
        """
        Get the JSON schema for job description extraction.

        This schema focuses exclusively on extracting job description content
        using comprehensive CSS selectors that work across various job boards,
        company career pages, and job posting platforms.

        Returns:
            Dictionary containing the extraction schema for Crawl4AI.
        """
        return {
            "name": "Job Description Content",
            "baseSelector": "body",
            "fields": [
                {
                    "name": "job_description",
                    "selector": ", ".join(
                        [
                            # Common job description containers
                            ".job-description",
                            ".jobDescription",
                            ".job-desc",
                            ".description",
                            ".job-details",
                            ".jobDetails",
                            ".job-detail",
                            ".position-description",
                            ".job-content",
                            ".jobContent",
                            ".job-posting-description",
                            ".role-description",
                            ".vacancy-description",
                            ".job-summary",
                            # Data attributes and IDs
                            "[data-testid='job-description']",
                            "[data-testid='jobDescription']",
                            "[data-testid='job-details']",
                            "[data-testid='description']",
                            "[data-automation='job-description']",
                            "[data-cy='job-description']",
                            "#job-description",
                            "#jobDescription",
                            "#job-details",
                            "#description",
                            # Common job board specific selectors
                            ".jobsearch-jobDescriptionText",  # Indeed
                            ".jobs-description__content",  # LinkedIn
                            ".jobDescriptionContent",  # Monster
                            ".jobDetailText",  # Glassdoor
                            ".show-more-less-html__markup",  # LinkedIn expanded
                            ".jobs-box__html-content",  # LinkedIn alternative
                            ".jobDescriptionWrapper",  # CareerBuilder
                            ".job-description-container",  # ZipRecruiter
                            ".jobDescText",  # Dice
                            ".gtmJobDescription",  # Stack Overflow Jobs
                            # Generic content containers that might contain job descriptions
                            "main .content",
                            "article .content",
                            ".main-content",
                            ".primary-content",
                            ".page-content",
                            ".body-content",
                            # Semantic HTML elements
                            "main",
                            "article",
                            "section[role='main']",
                            # Common wrapper classes
                            ".wrapper .description",
                            ".container .description",
                            ".content-wrapper .description",
                            ".page-wrapper .description",
                            # Alternative description class patterns
                            ".job-posting-content",
                            ".position-content",
                            ".role-content",
                            ".vacancy-content",
                            ".opening-description",
                            ".listing-description",
                            ".posting-description",
                            ".career-description",
                            ".opportunity-description",
                            # Company career page patterns
                            ".career-description",
                            ".careers-content",
                            ".job-opportunity",
                            ".position-details",
                            ".role-details",
                            ".job-info",
                            # Additional common patterns
                            ".job-posting-details",
                            ".position-posting",
                            ".role-posting",
                            ".job-listing-description",
                            ".career-listing",
                            ".opportunity-listing",
                            # Fallback to broader content areas
                            ".job-posting",
                            ".job-listing",
                            ".position-listing",
                            ".career-posting",
                            ".opportunity-posting",
                        ]
                    ),
                    "type": "html",
                    "default": "",
                }
            ],
        }

    async def _extract_job_description(self, url: str) -> Optional[str]:
        """
        Extract job description content using Crawl4AI with comprehensive selectors.

        Args:
            url: The job posting URL to extract from.

        Returns:
            Extracted job description as HTML string, or None if extraction fails.
        """
        # Configure browser for Crawl4AI
        browser_config = BrowserConfig(
            headless=self.headless,
            verbose=True,
            browser_type="chromium",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        )

        # Get the extraction schema
        schema = self._get_job_description_schema()
        extraction_strategy = JsonCssExtractionStrategy(schema, verbose=True)

        # Configure crawler run settings
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=extraction_strategy,
            page_timeout=self.page_timeout,
            # Enhanced JavaScript to handle various page interactions
            js_code=[
                # Handle cookie consent and privacy banners
                """
                (function() {
                    const acceptButtons = document.querySelectorAll(
                        'button[id*="accept"], button[class*="accept"], ' +
                        'button[id*="consent"], button[class*="consent"], ' +
                        'button[id*="agree"], button[class*="agree"], ' +
                        '[data-cookiebanner="accept"], #onetrust-accept-btn-handler, ' +
                        '.cookie-accept, .privacy-accept, .gdpr-accept'
                    );
                    acceptButtons.forEach(btn => {
                        if (btn.offsetParent !== null) btn.click();
                    });
                })();
                """,
                # Handle "Show more" or "Read more" buttons for job descriptions
                """
                (function() {
                    const showMoreButtons = document.querySelectorAll(
                        'button[class*="show-more"], button[class*="read-more"], ' +
                        'button[class*="expand"], a[class*="show-more"], ' +
                        'a[class*="read-more"], .show-more-button, .expand-button, ' +
                        '[data-testid="show-more"], [data-automation="show-more"]'
                    );
                    showMoreButtons.forEach(btn => {
                        if (btn.offsetParent !== null) btn.click();
                    });
                })();
                """,
                # Scroll to trigger lazy loading and reveal hidden content
                """
                (function() {
                    window.scrollTo(0, document.body.scrollHeight / 3);
                    setTimeout(() => {
                        window.scrollTo(0, document.body.scrollHeight * 2 / 3);
                        setTimeout(() => window.scrollTo(0, 0), 1000);
                    }, 1000);
                })();
                """,
                # Close any modal dialogs that might obstruct content
                """
                (function() {
                    const closeButtons = document.querySelectorAll(
                        '.modal-close, .dialog-close, .popup-close, ' +
                        'button[aria-label*="close"], button[aria-label*="Close"], ' +
                        '[data-dismiss="modal"], .close-button'
                    );
                    closeButtons.forEach(btn => {
                        if (btn.offsetParent !== null) btn.click();
                    });
                })();
                """,
            ],
            wait_for="networkidle",
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
                        return job_description.strip()
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

    async def scrape_job_posting(self, job_url: str) -> Optional[JobDetails]:
        """
        Extract job description from a job posting URL using Crawl4AI.

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
