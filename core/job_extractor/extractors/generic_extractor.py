from typing import Optional

from playwright.async_api import Page

import config.logging_config as logging_config
from core.job_extractor.utils.html_parser import html_to_markdown
from core.models.job_extractor import JobDetails

from .base_extractor import BaseExtractor
from .domain_selectors import (
    get_domain_config,
    get_selectors_for_url,
    get_timeout_for_url,
    should_wait_for_network_idle,
)

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

        # Configure base timeouts - these will be overridden by domain-specific configs
        if getattr(self, "fast_mode", False):
            self.default_navigation_timeout = 15000  # 15 seconds for navigation
            self.default_element_timeout = 3000  # 3 seconds for elements
            self.default_network_idle_timeout = 3000  # 3 seconds for network idle
        else:
            self.default_navigation_timeout = 20000  # 20 seconds for navigation
            self.default_element_timeout = 5000  # 5 seconds for elements
            self.default_network_idle_timeout = 5000  # 5 seconds for network idle

    async def extract_full_job_content(self, page: Page, job_url: str) -> str:
        """Extracts all relevant job posting content from a generic page using domain-specific selectors."""

        # Get domain-specific selectors for this URL
        content_selectors = get_selectors_for_url(job_url)

        # Get domain-specific timeout
        domain_timeout = get_timeout_for_url(job_url) * 1000  # Convert to milliseconds
        element_timeout = min(
            domain_timeout // 3, self.default_element_timeout
        )  # Use 1/3 of domain timeout or default, whichever is smaller

        # Log which domain configuration we're using
        domain_config = get_domain_config(job_url)
        if domain_config:
            logger.info(f"Using domain-specific selectors for {job_url}")
        else:
            logger.info(f"Using generic selectors for {job_url}")

        for selector in content_selectors:
            try:
                await page.wait_for_selector(
                    selector, timeout=element_timeout, state="visible"
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

        # Get domain-specific configuration
        domain_timeout_seconds = get_timeout_for_url(job_url)
        navigation_timeout = domain_timeout_seconds * 1000  # Convert to milliseconds
        should_wait_network_idle = should_wait_for_network_idle(job_url)
        network_idle_timeout = min(
            navigation_timeout // 2, self.default_network_idle_timeout
        )

        logger.info(
            f"Using domain-specific config: timeout={domain_timeout_seconds}s, "
            f"network_idle={should_wait_network_idle}, navigation_timeout={navigation_timeout}ms"
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
            page.set_default_timeout(navigation_timeout)

            logger.info(f"Navigating to {job_url}...")
            await page.goto(
                job_url, wait_until="domcontentloaded", timeout=navigation_timeout
            )

            # Only wait for network idle if the domain configuration says to
            if should_wait_network_idle:
                try:
                    await page.wait_for_load_state(
                        "networkidle", timeout=network_idle_timeout
                    )
                except Exception as e:
                    logger.warning(
                        f"Network idle wait timeout for {job_url}: {e}. Proceeding anyway."
                    )
            else:
                logger.info(f"Skipping network idle wait for {job_url} (domain config)")

            await self.handle_cookie_consent(page)

            extracted_content_html = await self.extract_full_job_content(page, job_url)

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
