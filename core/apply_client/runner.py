"""Orchestrate prepare -> browser fill -> status update."""

from __future__ import annotations

import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

from config.logging_config import get_logger
from core.apply_client.api_client import YarbaApplyClient
from core.apply_client.browser_agent import ApplyBrowserAgent
from core.apply_client.wait_for_posting import wait_for_posting_ready
from core.job_extractor.extract_job import JobExtractor
from core.job_extractor.page_extract import extract_description_from_page
from core.job_extractor.url_utils import job_posting_url_for_extraction

logger = get_logger(__name__)

DEFAULT_BROWSER_PROFILE = Path.home() / ".yarba" / "apply-browser"


class ApplyExtractionError(Exception):
    """Raised when the local job extractor cannot resolve a description."""


async def run_apply(
    *,
    api_base_url: str,
    token: str,
    job_url: str,
    headed: bool = True,
    submit: bool = False,
    max_steps: int = 40,
    model: str | None = None,
    browser_profile_dir: Path | None = DEFAULT_BROWSER_PROFILE,
    on_before_agent: Callable[[], Awaitable[None]] | None = None,
    on_review: Callable[[], Awaitable[None]] | None = None,
    on_human_required: Callable[[str], Awaitable[None]] | None = None,
) -> dict[str, Any]:
    client = YarbaApplyClient(api_base_url, token)
    posting_url = job_posting_url_for_extraction(job_url)
    headless_extractor = JobExtractor(headless=True, fast_mode=False)
    headless_extractor.manager.use_crawl4ai_fallback = True

    pdf_path: Path | None = None
    with tempfile.TemporaryDirectory(prefix="yarba-apply-") as tmp_dir:
        agent = ApplyBrowserAgent(
            model=model,
            max_steps=max_steps,
            submit_allowed=submit,
        )

        async with async_playwright() as playwright:
            profile_dir = browser_profile_dir or DEFAULT_BROWSER_PROFILE
            profile_dir.mkdir(parents=True, exist_ok=True)
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=not headed,
                viewport={"width": 1440, "height": 900},
            )
            page = context.pages[0] if context.pages else await context.new_page()

            logger.info("Opening job posting at %s", posting_url)
            await page.goto(posting_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(1500)

            if on_before_agent is not None:
                await wait_for_posting_ready(
                    page, job_url, manual_continue=on_before_agent
                )
            else:
                await wait_for_posting_ready(page, job_url)

            logger.info("Extracting job description from the current page...")
            description = await extract_description_from_page(page, job_url)
            if not description:
                logger.info(
                    "Live page extraction failed; retrying with headless JobExtractor"
                )
                job_details = await headless_extractor.extract_from_url(job_url)
                description = job_details.description if job_details else None

            if not description or not description.strip():
                raise ApplyExtractionError(
                    f"Job extractor could not resolve a description for {job_url}. "
                    "Open the full job posting (not only the apply form) and try again."
                )

            logger.info("Preparing tailored resume via API (usually 30–90 seconds)...")
            prepare_response = await client.prepare(
                job_url=job_url,
                job_description=description,
                compile_pdf=True,
            )
            application_id = prepare_response["application_id"]
            resume_id = prepare_response["resume_id"]
            application_profile = prepare_response["application_profile"]

            pdf_path = Path(tmp_dir) / f"{resume_id}.pdf"
            await client.download_resume_pdf(resume_id, pdf_path)
            logger.info("Downloaded resume PDF to %s", pdf_path)

            if job_url.rstrip("/") != page.url.rstrip("/"):
                logger.info("Navigating to apply URL %s", job_url)
                await page.goto(job_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(1500)

            logger.info("Starting LLM-driven apply navigation and form fill...")
            success, outcome = await agent.run(
                page,
                application_profile=application_profile,
                resume_pdf_path=pdf_path,
                on_human_required=on_human_required,
            )

            if on_review is not None:
                await on_review()
            elif headed and not submit:
                logger.info("Apply run finished — closing browser.")

            await context.close()

    status = "submitted" if outcome == "submitted" else "preview_ready"
    if not success:
        status = "failed"
        await client.update_application(
            application_id,
            status=status,
            error_message=outcome,
        )
    else:
        await client.update_application(application_id, status=status)

    return {
        "application_id": application_id,
        "resume_id": resume_id,
        "status": status,
        "outcome": outcome,
        "submit": submit,
    }
