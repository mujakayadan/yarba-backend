from playwright.async_api import Page

import config.logging_config as logging_config
from core.job_extractor.utils.html_parser import html_to_markdown
from core.models.job_extractor import JobDetails
from core.utils.url import url_has_domain

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
        """Initialize the generic job extractor

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
        """Handle cookie consent and other popups that might appear

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

    async def handle_cloudflare_challenge(self, page: Page) -> bool:
        """Check for and handle Cloudflare protection challenges

        Args:
            page: Playwright page

        Returns:
            bool: True if a Cloudflare challenge was detected
        """
        # Check for Cloudflare challenge indicators
        cloudflare_indicators = [
            "Cloudflare",
            "cloudflare",
            "challenge",
            "security check",
            "Ray ID",
            "Additional Verification Required",
            "waiting for",
            "to respond",
            "Checking your browser",
        ]

        try:
            # Get page content
            content = await page.content()
            page_text = await page.inner_text("body")

            # Check for Cloudflare indicators
            for indicator in cloudflare_indicators:
                if indicator in content or indicator in page_text:
                    logger.warning(
                        f"Cloudflare protection detected: '{indicator}' found on page"
                    )

                    # Wait longer to see if the challenge resolves
                    logger.info("Waiting for Cloudflare challenge to resolve...")
                    await page.wait_for_timeout(10000)  # Wait 10 seconds

                    # Check again after waiting
                    new_content = await page.content()
                    if "Cloudflare" in new_content or "Ray ID" in new_content:
                        logger.error("Cloudflare challenge still present after waiting")
                        return True
                    else:
                        logger.info("Cloudflare challenge appears to be resolved")
                        return False

            # No Cloudflare indicators found
            return False

        except Exception as e:
            logger.error(f"Error checking for Cloudflare challenge: {e}")
            return False

    async def scrape_job_posting(self, job_url: str) -> JobDetails | None:
        """Extract job details from a job posting URL

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

            # Use a more up-to-date and common user agent
            modern_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

            # Create context with settings to bypass bot detection
            context = await browser.new_context(
                viewport={
                    "width": 1920,
                    "height": 1080,
                },  # More common screen resolution
                user_agent=modern_user_agent,
                java_script_enabled=True,
                locale="en-US",  # Set locale
                timezone_id="America/New_York",  # Set timezone
                device_scale_factor=1,  # Standard scale
                is_mobile=False,
                has_touch=False,
                # Add additional headers that regular browsers typically include
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Sec-Ch-Ua": '"Chromium";v="123", "Google Chrome";v="123", "Not:A-Brand";v="99"',
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": '"Windows"',
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Upgrade-Insecure-Requests": "1",
                },
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
                if url_has_domain(job_url, "myworkdayjobs.com"):
                    try:
                        await page.wait_for_selector(
                            '[data-automation-id="jobPostingDescription"]',
                            timeout=navigation_timeout,
                            state="visible",
                        )
                        await page.wait_for_timeout(2000)
                    except Exception as e:
                        logger.warning(
                            "Workday posting description wait timed out for %s: %s",
                            job_url,
                            e,
                        )

            # First handle cookie consent
            await self.handle_cookie_consent(page)

            # Then check and handle any Cloudflare challenges
            cloudflare_detected = await self.handle_cloudflare_challenge(page)

            if cloudflare_detected:
                logger.warning(f"Cloudflare protection is blocking access to {job_url}")

                # Take screenshot for debugging (if in debug mode)
                try:
                    await page.screenshot(
                        path=f"debug/output/cloudflare_block_{hash(job_url)}.png"
                    )
                    logger.info("Saved Cloudflare block screenshot for debugging")
                except Exception as e:
                    logger.debug(f"Could not save Cloudflare screenshot: {e}")

                # Try to reload the page once more
                logger.info("Attempting to reload page after Cloudflare detection...")
                await page.reload(
                    timeout=navigation_timeout, wait_until="domcontentloaded"
                )
                await page.wait_for_timeout(5000)  # Wait a bit after reload

            # Extract content
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
