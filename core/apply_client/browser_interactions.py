"""Robust Playwright interactions for ATS form controls."""

from __future__ import annotations

from playwright.async_api import Locator, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from config.logging_config import get_logger

logger = get_logger(__name__)


async def fill_control(page: Page, selector: str, value: str) -> bool:
    """Fill a field; Workday and similar sites often need click-before-fill."""
    locator = page.locator(selector).first
    try:
        await locator.wait_for(state="visible", timeout=5000)
        await locator.scroll_into_view_if_needed(timeout=3000)
        await locator.click(timeout=5000)
        await locator.fill(value, timeout=5000)
        return True
    except PlaywrightTimeoutError:
        logger.debug("Standard fill failed for %s, trying press_sequentially", selector)
    try:
        await locator.click(timeout=5000)
        await locator.press_sequentially(value, delay=25)
        return True
    except PlaywrightTimeoutError as exc:
        logger.warning("Could not fill %s: %s", selector, exc)
        return False


async def _is_hidden_duplicate(locator: Locator) -> bool:
    aria_hidden = await locator.get_attribute("aria-hidden")
    if aria_hidden == "true":
        return True
    tabindex = await locator.get_attribute("tabindex")
    return tabindex == "-2"


async def _click_locator(locator: Locator, *, selector: str) -> bool:
    try:
        await locator.wait_for(state="visible", timeout=5000)
        await locator.scroll_into_view_if_needed(timeout=3000)
        await locator.click(timeout=5000)
        return True
    except PlaywrightTimeoutError:
        logger.debug("Normal click failed for %s, trying force click", selector)
    try:
        await locator.click(force=True, timeout=5000)
        return True
    except PlaywrightTimeoutError:
        logger.debug("Force click failed for %s, trying DOM click", selector)
    try:
        await locator.evaluate("el => el.click()")
        return True
    except Exception as exc:
        logger.warning("Could not click %s: %s", selector, exc)
        return False


async def click_control(page: Page, selector: str) -> bool:
    """Click a control; skip aria-hidden duplicates and use force/JS fallback."""
    locators = page.locator(selector)
    count = await locators.count()
    if count == 0:
        logger.warning("Could not click %s: no matching elements", selector)
        return False

    for index in range(count):
        locator = locators.nth(index)
        if await _is_hidden_duplicate(locator):
            continue
        if await _click_locator(locator, selector=selector):
            return True

    return await _click_locator(locators.first, selector=selector)


async def click_locator(locator: Locator, *, label: str = "control") -> bool:
    """Click a resolved locator with force/JS fallback."""
    return await _click_locator(locator, selector=label)


async def click_button_by_role(page: Page, names: tuple[str, ...]) -> bool:
    """Click the first visible button matching one of the accessible names."""
    for name in names:
        locator = page.get_by_role("button", name=name)
        count = await locator.count()
        for index in range(count):
            candidate = locator.nth(index)
            if await _is_hidden_duplicate(candidate):
                continue
            if await _click_locator(candidate, selector=f'button:"{name}"'):
                return True
    return False
