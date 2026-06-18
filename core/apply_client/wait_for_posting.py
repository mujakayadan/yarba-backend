"""Wait for a job posting page to be ready for description extraction."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from config.logging_config import get_logger
from core.job_extractor.page_extract import WORKDAY_DESCRIPTION_SELECTOR
from core.job_extractor.url_utils import job_posting_url_for_extraction

logger = get_logger(__name__)

AUTO_WAIT_INTERVAL_MS = 2000
AUTO_WAIT_MAX_ATTEMPTS = 45  # ~90 seconds


async def wait_for_posting_ready(
    page: Page,
    job_url: str,
    *,
    manual_continue: Callable[[], Awaitable[None]] | None = None,
) -> None:
    """Wait until the posting looks ready, or the user continues manually."""
    posting_url = job_posting_url_for_extraction(job_url)

    if "myworkdayjobs.com" in posting_url:
        await _auto_wait_workday(page, manual_continue)
        return

    await _auto_wait_generic(page, manual_continue)


async def _auto_wait_workday(
    page: Page,
    manual_continue: Callable[[], Awaitable[None]] | None,
) -> None:
    logger.info(
        "Auto-waiting for job description in the browser "
        "(log in or accept cookies there if needed)."
    )

    for attempt in range(AUTO_WAIT_MAX_ATTEMPTS):
        try:
            if await page.locator(WORKDAY_DESCRIPTION_SELECTOR).first.is_visible(
                timeout=500
            ):
                logger.info("Job description detected — continuing.")
                await page.wait_for_timeout(1000)
                return
        except PlaywrightTimeoutError:
            pass

        if attempt > 0 and attempt % 5 == 0:
            elapsed = attempt * AUTO_WAIT_INTERVAL_MS // 1000
            logger.info("Still waiting for job description… (%ss)", elapsed)
        await page.wait_for_timeout(AUTO_WAIT_INTERVAL_MS)

    logger.warning("Timed out waiting for job description; continuing anyway.")
    if manual_continue is not None:
        await manual_continue()


async def _auto_wait_generic(
    page: Page,
    manual_continue: Callable[[], Awaitable[None]] | None,
) -> None:
    logger.info("Auto-waiting for job posting content to load...")

    for attempt in range(AUTO_WAIT_MAX_ATTEMPTS):
        ready = await page.evaluate(
            """() => {
                const heading = document.querySelector("h1, h2");
                const textLength = document.body?.innerText?.trim().length || 0;
                return Boolean(heading && textLength > 400);
            }"""
        )
        if ready:
            logger.info("Posting content detected — continuing.")
            await page.wait_for_timeout(1000)
            return

        if attempt > 0 and attempt % 5 == 0:
            elapsed = attempt * AUTO_WAIT_INTERVAL_MS // 1000
            logger.info("Still waiting for posting content… (%ss)", elapsed)
        await page.wait_for_timeout(AUTO_WAIT_INTERVAL_MS)

    logger.warning("Timed out waiting for posting content; continuing anyway.")
    if manual_continue is not None:
        await manual_continue()
