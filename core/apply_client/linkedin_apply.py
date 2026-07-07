"""LinkedIn-specific helpers for the apply browser agent."""

from __future__ import annotations

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from config.logging_config import get_logger

logger = get_logger(__name__)

EASY_APPLY_SELECTORS = (
    'button[data-tracking-control-name="public_jobs_apply-link-onsite"]',
    'button[data-tracking-control-name="public_jobs_apply-link-offsite"]',
    "button.jobs-apply-button",
    "button.jobs-apply-button--top-card",
    'button:has-text("Easy Apply")',
)


async def try_open_easy_apply(page: Page) -> bool:
    """Click LinkedIn Easy Apply if the button is visible."""
    for selector in EASY_APPLY_SELECTORS:
        try:
            locator = page.locator(selector).first
            if await locator.is_visible(timeout=1500):
                logger.info("Clicking LinkedIn apply control: %s", selector)
                await locator.click(timeout=5000)
                await page.wait_for_timeout(2000)
                return True
        except PlaywrightTimeoutError:
            continue
    return False
