"""Extract job descriptions from an already-open Playwright page."""

from __future__ import annotations

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from config.logging_config import get_logger
from core.job_extractor.extractors.generic_extractor import GenericExtractor
from core.job_extractor.url_utils import job_posting_url_for_extraction
from core.job_extractor.utils.html_parser import html_to_markdown

logger = get_logger(__name__)

WORKDAY_DESCRIPTION_SELECTOR = '[data-automation-id="jobPostingDescription"]'


async def extract_description_from_page(page: Page, job_url: str) -> str | None:
    """Scrape a job description from the current browser page."""
    posting_url = job_posting_url_for_extraction(job_url)

    if "myworkdayjobs.com" in posting_url:
        try:
            await page.wait_for_selector(
                WORKDAY_DESCRIPTION_SELECTOR,
                timeout=30000,
                state="visible",
            )
            await page.wait_for_timeout(1500)
        except PlaywrightTimeoutError:
            logger.warning("Workday description selector not visible on %s", page.url)

    extractor = GenericExtractor(headless=True)
    html = await extractor.extract_full_job_content(page, posting_url)
    if not html or len(html.strip()) < 150:
        return None

    markdown = html_to_markdown(html)
    if not markdown or len(markdown.strip()) < 100:
        return None
    return markdown
