import logging
from typing import Optional

from playwright.async_api import Page

from core.job_extractor.utils.html_parser import html_to_markdown
from core.models.job_extractor import JobDetails

from ..settings import settings
from .base_extractor import BaseExtractor

logger = logging.getLogger(__name__)


class LinkedInExtractor(BaseExtractor):
    """
    Specialized scraper for LinkedIn job postings that can bypass anti-bot measures
    """

    def __init__(self, headless: bool = True):
        """
        Initialize the LinkedIn scraper

        Args:
            headless: Whether to run the browser in headless mode
        """
        super().__init__(headless=headless)

    async def get_full_job_content(self, page: Page) -> Optional[str]:
        """Extracts the full job content from a LinkedIn job page."""
        # Updated main content selector based on user-provided HTML
        job_posting_main_content_selector = "div.description__text--rich"

        # This selector remains the same as it was confirmed by user HTML for the button itself
        show_more_button_selector = (
            "button[data-tracking-control-name='public_jobs_show-more-html-btn']"
        )

        async def click_show_more_robustly(
            parent_element, button_selector_text, context_str
        ):
            await self.handle_cookie_consent(page)
            await self.handle_sign_in_modal(page)

            for attempt in range(settings.li_show_more_attempts):
                await self.handle_cookie_consent(page)
                await self.handle_sign_in_modal(page)
                try:
                    button_element = None
                    if parent_element:
                        if not await parent_element.is_visible():
                            logger.info(
                                f"Attempt {attempt + 1} ({context_str}): Parent element for 'Show more' not visible. Skipping click."
                            )
                            return False
                        button_element = await parent_element.query_selector(
                            button_selector_text
                        )
                    else:
                        button_element = await page.query_selector(button_selector_text)

                    if button_element and await button_element.is_visible():
                        is_expanded = await button_element.get_attribute(
                            "aria-expanded"
                        )
                        if is_expanded == "false":
                            logger.info(
                                f"Attempt {attempt + 1} ({context_str}): Clicking 'Show more' button with selector '{button_selector_text}'."
                            )
                            await button_element.wait_for_element_state(
                                "visible", timeout=settings.element_timeout_ms
                            )
                            await button_element.wait_for_element_state(
                                "enabled", timeout=settings.element_timeout_ms
                            )
                            await button_element.click(
                                timeout=settings.li_show_more_click_timeout_ms
                            )

                            # Wait for aria-expanded to become true or timeout
                            try:
                                await page.wait_for_function(
                                    f"""(selector) => {{
                                        const el = document.querySelector(selector);
                                        return el && el.getAttribute("aria-expanded") === "true";
                                    }}""",
                                    button_selector_text,
                                    timeout=settings.li_show_more_post_click_wait_ms,
                                )
                                logger.info(
                                    f"'Show more' ({context_str}) successfully expanded (aria-expanded is true)."
                                )
                                return True
                            except Exception as e_aria:
                                logger.warning(
                                    f"Attempt {attempt + 1} ({context_str}): 'Show more' clicked, but aria-expanded did not become true within timeout: {e_aria}"
                                )
                        else:
                            logger.info(
                                f"'Show more' ({context_str}) already expanded or not applicable."
                            )
                            return True
                    else:
                        logger.info(
                            f"Attempt {attempt + 1} ({context_str}): 'Show more' button not visible/found."
                        )

                except Exception as e_sm_click:
                    logger.warning(
                        f"Attempt {attempt + 1} ({context_str}) to click 'Show more' failed: {e_sm_click}"
                    )

                if attempt < settings.li_show_more_attempts - 1:
                    logger.info(
                        f"Waiting before retrying 'Show more' ({context_str})..."
                    )
                    await page.wait_for_timeout(1000)
            return False

        try:
            await self.handle_cookie_consent(page)
            await self.handle_sign_in_modal(page)

            logger.info(
                f"Attempting to find main job content area with: {job_posting_main_content_selector}"
            )
            main_content_element = await page.query_selector(
                job_posting_main_content_selector
            )

            if main_content_element:
                logger.info(
                    f"Found main job content element with '{job_posting_main_content_selector}'."
                )
                await self.handle_cookie_consent(page)
                await self.handle_sign_in_modal(page)

                # The "Show more" button might be nested within a <section> inside the main_content_element
                # or could be a direct child. Let's try to find it within main_content_element.
                # We will pass main_content_element as the parent for click_show_more_robustly.
                await click_show_more_robustly(
                    main_content_element, show_more_button_selector, "main content"
                )

                full_content_html = await main_content_element.inner_html()
                if full_content_html and len(full_content_html.strip()) > 150:
                    logger.info(
                        f"Successfully extracted content from '{job_posting_main_content_selector}'."
                    )
                    return full_content_html.strip()
                else:
                    logger.info(
                        f"Content from '{job_posting_main_content_selector}' too short/empty even after 'show more'."
                    )
            else:
                logger.info(
                    f"Main job content selector '{job_posting_main_content_selector}' not found."
                )

        except Exception as e_main:
            logger.warning(
                f"Error with main content: {e_main}. Trying specific description section."
            )

        logger.info(
            "Attempting broader fallback selectors for job content if primary method failed."
        )
        fallback_selectors = [
            ".jobs-description__content",  # Old primary, now a fallback
            ".job-description",
            ".job-details",
            "#job-details",
            "article[class*='job']",
            "main[class*='job']",
        ]
        for alt_selector in fallback_selectors:
            try:
                element = await page.query_selector(alt_selector)
                if element:
                    # Before extracting, ensure any modals are gone
                    await self.handle_cookie_consent(page)
                    await self.handle_sign_in_modal(page)
                    await element.wait_for_element_state(
                        "visible", timeout=settings.element_timeout_ms
                    )
                    content_html = await element.inner_html()
                    if content_html and len(content_html.strip()) > 150:
                        logger.info(f"Using fallback content selector: {alt_selector}")
                        return content_html.strip()
            except Exception as ex_alt:
                logger.debug(
                    f"Fallback content selector {alt_selector} failed: {ex_alt}"
                )
                continue

        logger.warning("Failed to retrieve job content with any method.")
        return None

    async def handle_cookie_consent(self, page: Page) -> None:
        """Handle cookie consent banners on LinkedIn"""
        for selector in settings.cookie_consent_selectors:
            try:
                button = await page.query_selector(selector)
                if button and await button.is_visible(
                    timeout=settings.modal_check_timeout_ms
                ):
                    logger.info(f"Clicking cookie consent button: {selector}")
                    await button.click(timeout=settings.modal_dismiss_timeout_ms)
                    await page.wait_for_timeout(500)
                    logger.info("Cookie consent clicked.")
                    return
            except Exception as e:
                logger.debug(f"Cookie button {selector} not found or error: {e}")

    async def handle_sign_in_modal(self, page: Page) -> None:
        """Handle sign-in modal popup on LinkedIn"""
        try:
            if await page.is_visible(
                settings.li_signin_modal_overlay_selector,
                timeout=settings.modal_check_timeout_ms,
            ):
                logger.info("Sign-in modal detected. Attempting to dismiss...")

                # Try the highly specific user-provided selector first
                user_specific_dismiss_selector = 'button[data-tracking-control-name="public_jobs_contextual-sign-in-modal_modal_dismiss"]'
                try:
                    dismiss_button = await page.query_selector(
                        user_specific_dismiss_selector
                    )
                    if dismiss_button and await dismiss_button.is_visible(
                        timeout=settings.modal_check_timeout_ms
                    ):
                        logger.info(
                            f"Trying to click dismiss button with user-specific selector: {user_specific_dismiss_selector}"
                        )
                        await dismiss_button.click(
                            timeout=settings.modal_dismiss_timeout_ms
                        )
                        await page.wait_for_timeout(500)
                        if not await page.is_visible(
                            settings.li_signin_modal_overlay_selector, timeout=500
                        ):
                            logger.info(
                                "Modal was successfully dismissed by user-specific button click."
                            )
                            return
                        else:
                            logger.warning(
                                "Modal still visible after user-specific button click."
                            )
                    else:
                        logger.debug(
                            "User-specific dismiss button not found or not visible."
                        )
                except Exception as e:
                    logger.debug(
                        f"Failed to click user-specific dismiss button {user_specific_dismiss_selector}: {e}"
                    )

                # If user-specific selector fails or modal still visible, try existing configured selectors
                if await page.is_visible(
                    settings.li_signin_modal_overlay_selector,
                    timeout=settings.modal_check_timeout_ms,
                ):  # Re-check if modal is still there
                    for selector in settings.li_signin_dismiss_selectors:
                        try:
                            dismiss_button = await page.query_selector(selector)
                            if dismiss_button and await dismiss_button.is_visible(
                                timeout=settings.modal_check_timeout_ms
                            ):
                                logger.info(
                                    f"Trying to click dismiss button with selector: {selector}"
                                )
                                await dismiss_button.click(
                                    timeout=settings.modal_dismiss_timeout_ms
                                )
                                await page.wait_for_timeout(500)
                                if not await page.is_visible(
                                    settings.li_signin_modal_overlay_selector,
                                    timeout=500,
                                ):
                                    logger.info(
                                        "Modal was successfully dismissed by button click."
                                    )
                                    return
                        except Exception as e:
                            logger.debug(
                                f"Failed to click dismiss button {selector}: {e}"
                            )

                # Fallback to Escape key if button clicks failed or modal still visible
                if await page.is_visible(
                    settings.li_signin_modal_overlay_selector,
                    timeout=settings.modal_check_timeout_ms,
                ):  # Re-check again
                    logger.info(
                        "Pressing Escape key to dismiss modal as button clicks failed or modal still visible..."
                    )
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(500)
                    if not await page.is_visible(
                        settings.li_signin_modal_overlay_selector, timeout=500
                    ):
                        logger.info("Modal was dismissed by pressing Escape.")
                        return
                    logger.warning(
                        "Sign-in modal still visible after all dismiss attempts."
                    )
            else:
                logger.info("No sign-in modal detected.")
        except Exception as e:
            logger.debug(f"Error during sign-in modal handling: {e}")

    async def scrape_job_posting(self, job_url: str) -> Optional[JobDetails]:
        """Scrapes a LinkedIn job posting page for its content."""
        logger.info(f"LinkedInExtractor: Fetching job details from: {job_url}")
        extracted_content_html = None
        job_title = None
        company_name = None

        try:
            # Initialize Playwright
            logger.info(f"Initializing Playwright for {job_url}")
            playwright = await self.init_playwright()

            # Launch browser
            browser_launch_args = []
            if settings.run_in_docker:  # Assuming you have a setting for this
                browser_launch_args.extend(["--no-sandbox", "--disable-dev-shm-usage"])

            browser = await playwright.chromium.launch(
                headless=self.headless, args=browser_launch_args
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                java_script_enabled=True,
                viewport={"width": 1366, "height": 768},
            )
            page = await context.new_page()
            page.set_default_navigation_timeout(settings.navigation_timeout_ms)

            try:
                logger.info(f"Navigating to {job_url}...")
                await page.goto(job_url, wait_until="domcontentloaded")

                logger.info("Page loaded. Waiting for network idle...")
                try:
                    await page.wait_for_load_state(
                        "networkidle", timeout=settings.network_idle_timeout_ms
                    )
                except Exception as e_ni:
                    logger.warning(
                        f"Network idle timeout for {job_url}: {e_ni}. Proceeding."
                    )

                await self.handle_cookie_consent(page)
                await self.handle_sign_in_modal(page)

                title_selectors = [
                    ".job-title",
                    ".jobs-unified-top-card__job-title",
                    ".top-card-layout__title",
                    "h1[class*='title']",
                    "h2[class*='title']",
                ]
                for ts_selector in title_selectors:
                    try:
                        title_element = await page.query_selector(ts_selector)
                        if title_element:
                            job_title = await title_element.inner_text()
                            job_title = job_title.strip() if job_title else None
                            if job_title:
                                logger.info(f"Extracted job title: {job_title}")
                                break
                    except Exception as e_title:
                        logger.debug(f"Title selector {ts_selector} failed: {e_title}")
                if not job_title:
                    logger.warning("Job title could not be extracted.")

                # Extract Company Name
                company_name_selector = "a.topcard__org-name-link"
                try:
                    company_element = await page.query_selector(company_name_selector)
                    if company_element:
                        company_name = await company_element.inner_text()
                        company_name = company_name.strip() if company_name else None
                        if company_name:
                            logger.info(f"Extracted company name: {company_name}")
                        else:
                            logger.warning(
                                "Company name element found, but text is empty."
                            )
                    else:
                        logger.warning(
                            f"Company name selector '{company_name_selector}' not found."
                        )
                except Exception as e_company:
                    logger.warning(
                        f"Error extracting company name with selector '{company_name_selector}': {e_company}"
                    )

                extracted_content_html = await self.get_full_job_content(page)

            except Exception as e:
                logger.error(
                    f"Major error during LinkedIn scraping for {job_url}: {e}",
                    exc_info=True,
                )
                return None
            finally:
                logger.info("Closing browser for LinkedIn extractor...")
                if "browser" in locals() and browser:
                    await browser.close()
                if "playwright" in locals() and playwright:
                    await playwright.stop()
        except Exception as e:
            logger.error(
                f"Critical error in LinkedInExtractor for {job_url}: {e}", exc_info=True
            )
            return None

        if not extracted_content_html or len(extracted_content_html.strip()) < 150:
            logger.warning(
                f"LinkedInExtractor: Failed to extract sufficient content from {job_url}. Aborting."
            )
            return None

        # Clean the HTML description to Markdown
        cleaned_description_body = html_to_markdown(extracted_content_html)

        # Prepare the full description string with title and company if available
        full_description_parts = []
        if job_title:
            full_description_parts.append(f"Title: {job_title}")
        if company_name:
            full_description_parts.append(f"Company: {company_name}")
        if cleaned_description_body:
            full_description_parts.append(f"\n{cleaned_description_body}")

        final_description = "\n\n".join(full_description_parts)

        if (
            not final_description or len(final_description.strip()) < 100
        ):  # Check length of the combined string
            logger.warning(
                f"Final description for {job_url} is too short. Original HTML length: {len(extracted_content_html)}, Markdown body length: {len(cleaned_description_body) if cleaned_description_body else 0}"
            )
            return None

        # The JobDetails model no longer has title or company_name fields explicitly.
        # All info is consolidated into the description.
        return JobDetails(description=final_description)
