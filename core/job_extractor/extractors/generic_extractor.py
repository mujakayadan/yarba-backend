from typing import Optional

from playwright.async_api import Page

import config.logging_config as logging_config
from core.job_extractor.utils.html_parser import html_to_markdown
from core.models.job_extractor import JobDetails

from .base_extractor import BaseExtractor

logger = logging_config.get_logger(__name__)


class GenericExtractor(BaseExtractor):
    """Generic job extractor for non-LinkedIn sites"""

    def __init__(self, headless: bool = True, fast_mode: bool = True):
        """
        Initialize the generic job extractor

        Args:
            headless: Whether to run the browser in headless mode
            fast_mode: Whether to use faster scraping with shorter timeouts
        """
        super().__init__(headless=headless, fast_mode=fast_mode)

        # Configure timeouts based on mode
        if getattr(self, "fast_mode", False):
            self.navigation_timeout = 30000  # 30 seconds for navigation
            self.element_timeout = 3000  # 3 seconds for elements (was 5)
            self.network_idle_timeout = 3000  # 3 seconds for network idle (was 5)
        else:
            self.navigation_timeout = 60000  # 60 seconds for navigation
            self.element_timeout = 7000  # 7 seconds for elements (was 10)
            self.network_idle_timeout = 7000  # 7 seconds for network idle (was 15)

    async def extract_full_job_content(self, page: Page) -> str:
        """Extracts all relevant job posting content from a generic page."""
        # Using existing description selectors as they are quite broad
        content_selectors = [
            # Added for Lever.co and similar structures (prioritized)
            "div.content-wrapper.posting-page > div.content",  # Lever: main content area including header and all sections
            "div[data-qa='job-description']",  # Lever: job description section
            "section[data-qa='job-description']",  # Lever: job description section (as section)
            # Greenhouse job board selector
            "div.job__description.body",
            # Common specific IDs for job descriptions
            "#job-description",
            "#jobDescription",  # Common variation
            # Specific attribute selectors
            "div[name='cwsJobDescription']",  # Taleo specific
            "[data-automation='jobDescription']",  # Common automation hook
            "div[data-automation-id='jobDescription']",  # Another common data-automation variant
            # Specific class names (exact match)
            ".jobDescriptionContent",
            ".job-description-content",  # Common variation
            ".job-posting-content",
            ".job-details-content",
            # Tag with specific class combinations
            "article.job-description",
            "section.job-description",
            "div.job-description",
            "article.job-details",
            "section.job-details",
            "div.job-details",
            "article.description",
            "section.description",
            "div.description",  # More specific than just .description
            # Attribute "class" contains value (more general, so after exact matches)
            "article[class*='job-description']",
            "section[class*='job-description']",
            "div[class*='job-description']",
            "article[class*='jobDetails']",  # Camel case variation for details
            "section[class*='jobDetails']",
            "div[class*='jobDetails']",
            "div[class*='description']",  # Use cautiously, can be broad
            # Common main content container IDs and classes
            "#content",
            "#main-content",
            "div.content",  # Exact class 'content'
            "div.main-content",  # Exact class 'main-content'
            "div.job-content",
            "div[class*='content']",  # Fallback for class containing 'content', moved lower
            # Very specific selector from a previous issue (lower priority as it's very specific)
            "div._8muv._ar_h",
            # Broad HTML5 semantic tags as last resort for text content
            "article",  # Fallback to article tag
            "main",  # Fallback to main tag
        ]

        for selector in content_selectors:
            try:
                await page.wait_for_selector(
                    selector, timeout=self.element_timeout, state="visible"
                )
                element = await page.query_selector(selector)
                if element:
                    content = await element.inner_html()
                    # Keep a reasonable minimum length, but it's for the whole content now
                    if content and len(content.strip()) > 150:
                        logger.info(f"Found job content with selector: {selector}")
                        return content.strip()
            except Exception as e:
                logger.debug(f"Content selector {selector} failed: {e}")
                continue

        # Ultimate fallback to body if nothing else works
        try:
            body = await page.query_selector("body")
            if body:
                content = await body.inner_html()
                logger.warning("Falling back to full body content for job details.")
                return content.strip()
        except Exception as e:
            logger.error(f"Error getting body content: {e}")

        return ""

    async def handle_cookie_consent(self, page: Page) -> None:
        """
        Handle cookie consent and other popups that might appear

        Args:
            page: Playwright page
        """
        cookie_buttons = [
            "button:text-matches('Accept', 'i')",
            "button:text-matches('Agree', 'i')",
            "button:text-matches('Got it', 'i')",
            "button:text-matches('Continue', 'i')",
            "button[data-cookiebanner='accept']",
            "#onetrust-accept-btn-handler",  # Common cookie consent id
        ]

        for button_selector in cookie_buttons:
            try:
                button = await page.query_selector(button_selector)
                if (
                    button and await button.is_visible()
                ):  # Check visibility before clicking
                    logger.info(f"Clicking consent button: {button_selector}")
                    await button.click(timeout=3000)
                    await page.wait_for_timeout(1000)  # Wait for action to complete
                    logger.info(f"Clicked: {button_selector}")
                    return  # Assume one consent banner is enough
            except Exception as e:
                logger.debug(
                    f"Cookie consent button {button_selector} not found or error: {e}"
                )
                continue

    async def scrape_job_posting(self, job_url: str) -> Optional[JobDetails]:
        """
        Extract job details from a job posting URL

        Args:
            job_url: URL of the job posting

        Returns:
            A JobDetails Pydantic model instance or None if extraction fails.
        """
        logger.info(
            f"GenericExtractor: Extracting full job content from URL: {job_url}"
        )
        extracted_content_html = ""
        playwright = None
        browser = None

        try:
            logger.info(f"Initializing Playwright for {job_url}")
            playwright = await self.init_playwright()

            browser = await playwright.chromium.launch(headless=self.headless)

            context = await browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                java_script_enabled=True,
            )

            page = await context.new_page()
            page.set_default_timeout(self.navigation_timeout)

            logger.info(f"Navigating to {job_url}...")
            await page.goto(
                job_url, wait_until="domcontentloaded", timeout=self.navigation_timeout
            )

            try:
                await page.wait_for_load_state(
                    "networkidle", timeout=self.network_idle_timeout
                )
            except Exception as e:
                logger.warning(
                    f"Network idle wait timeout for {job_url}: {e}. Proceeding anyway."
                )

            await self.handle_cookie_consent(page)

            extracted_content_html = await self.extract_full_job_content(page)

        except Exception as e:
            logger.error(
                f"Error during GenericExtractor scraping for {job_url}: {e}",
                exc_info=True,
            )
            return None  # Ensure None is returned on error
        finally:
            if browser:
                logger.info(f"Closing browser for {job_url} (GenericExtractor)")
                await browser.close()
            if playwright:  # Ensure playwright is not None before calling stop
                logger.info(f"Stopping Playwright for {job_url} (GenericExtractor)")
                await playwright.stop()

        if not extracted_content_html or len(extracted_content_html.strip()) < 150:
            logger.warning(
                f"GenericExtractor: Failed to extract sufficient content from {job_url}. Aborting."
            )
            return None

        cleaned_description = html_to_markdown(extracted_content_html)
        return JobDetails(description=cleaned_description)
