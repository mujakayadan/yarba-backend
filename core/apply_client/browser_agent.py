"""LLM-driven browser agent that fills job application forms."""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import litellm
from litellm import acompletion
from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from config.logging_config import get_logger
from config.settings import settings
from core.apply_client.auth_autofill import (
    autofill_auth_fields_from_profile,
    resolve_auth_mode,
    submit_auth_and_wait,
    switch_to_sign_in_form,
)
from core.apply_client.browser_interactions import click_control, fill_control
from core.apply_client.page_navigation import (
    can_finish_application,
    count_interactive_fields,
    is_auth_form_ready,
    is_email_verification_page,
    is_likely_login_form,
)
from core.apply_client.page_snapshot import (
    profile_payload_for_prompt,
    snapshot_page,
    snapshot_signature,
)
from core.apply_client.schemas import AgentStepResponse, BrowserAction

logger = get_logger(__name__)

_LITELLM_LOGGERS = ("LiteLLM", "litellm", "litellm.utils", "httpx", "httpcore")
_WAIT_MS = 2000
_EMPTY_SNAPSHOT_RETRIES = 5
_STALL_STEPS = 3
_MAX_AUTH_STUCK_ATTEMPTS = 3


def _quiet_litellm_console() -> None:
    litellm.set_verbose = False
    for name in _LITELLM_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


SYSTEM_PROMPT = """You are a job application automation agent for ANY careers site.

You only act through page.fields: each item has tag, label, input_type, value, and an exact
`selector`. Use ONLY those selectors — never invent CSS.

Data policy (strict):
- application_profile contains ALL answers you may use. Check it before every fill.
- Fill ONLY from application_profile. Never invent or guess values.
- If a field needs data that is null, empty, or missing in application_profile, do NOT fill it.
  Use action=need_human with reason missing_profile_data and name the field in reason.
- NEVER invent work authorization, sponsorship, age, relocation, salary, or EEO answers.
- If apply_account_password is null and a password is required, use action=need_human with
  reason missing_profile_data (careers-site password not configured).

Human-in-the-loop (never automate these):
- CAPTCHA → action=need_human, reason captcha
- Email verification code/link → action=need_human, reason email_verification
- SMS / phone verification → action=need_human, reason sms_verification
- Do NOT use action=fail for captcha or verification — always need_human.

Navigation:
- Handle cookie/consent banners by clicking the appropriate control in page.fields.
- Prefer manual/direct apply on the employer site over third-party OAuth (LinkedIn/Google).
- Do NOT click header Sign In (e.g. utilityButtonSignIn) when a Create Account form is on page.
- On auth forms: when email/password fields are already filled, click Create Account or Sign In
  (whichever matches the form) — do not wait repeatedly with action=wait.
- Do NOT use action=done or submit_ready on auth/landing pages.

Form filling:
- Skip fields that already show the correct value in page.fields[].value.
- For file uploads use action=upload (resume PDF attached server-side).
- submit_ready=true only when the main application form looks complete AND a submit control
  is in page.fields. Never submit_ready on auth pages.

Other:
- action=wait briefly after navigation clicks.
- action=done only when the main form is filled and submit_allowed is false.
- action=fail only for unrecoverable technical errors (not captcha/verification/missing data).
- Return compact JSON matching the schema only.
"""


class ApplyBrowserAgent:
    """Runs an observe-think-act loop against a job application page."""

    def __init__(
        self,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        max_steps: int = 40,
        submit_allowed: bool = False,
    ) -> None:
        self.model = model or settings.llm.default_model
        self.temperature = temperature
        self.max_steps = max_steps
        self.submit_allowed = submit_allowed
        _quiet_litellm_console()

    @staticmethod
    def _api_key_for_model(model: str) -> str | None:
        model_lower = model.lower()
        if "gpt" in model_lower or "text-embedding" in model_lower:
            return settings.llm.openai_api_key
        if "claude" in model_lower:
            return settings.llm.anthropic_api_key
        if "gemini" in model_lower:
            return settings.llm.gemini_api_key
        return settings.llm.openai_api_key

    async def run(
        self,
        page: Page,
        *,
        application_profile: dict[str, Any],
        resume_pdf_path: Path | None,
        on_human_required: Callable[[str], Awaitable[None]] | None = None,
    ) -> tuple[bool, str]:
        history: list[str] = []
        logger.info(
            "Starting LLM apply agent (%s steps max, dry_run=%s)",
            self.max_steps,
            not self.submit_allowed,
        )
        if not application_profile.get("apply_account_password"):
            logger.warning(
                "No apply_account_password on profile — save one under Profile → "
                "Application Settings and ensure your PAT has applications:credentials:read"
            )

        empty_snapshots = 0
        prev_signature: tuple[str, tuple[tuple[str, str | None], ...]] | None = None
        stall_steps = 0
        auth_stuck_attempts = 0
        prefer_sign_in = False

        for step in range(1, self.max_steps + 1):
            snapshot = await snapshot_page(page)
            field_count = len(snapshot.fields)
            interactive = count_interactive_fields(snapshot)

            if field_count == 0:
                empty_snapshots += 1
                if empty_snapshots >= _EMPTY_SNAPSHOT_RETRIES:
                    return False, "no_page_controls"
                logger.info(
                    "Waiting for page controls to appear (step %s/%s)...",
                    step,
                    self.max_steps,
                )
                await page.wait_for_timeout(_WAIT_MS)
                continue
            empty_snapshots = 0

            if is_likely_login_form(snapshot):
                if is_email_verification_page(snapshot):
                    logger.info("Email verification step detected")
                    if on_human_required is not None:
                        await on_human_required("email_verification")
                    auth_stuck_attempts = 0
                    prefer_sign_in = False
                    continue

                contact = application_profile.get("contact") or {}
                auth_mode = resolve_auth_mode(snapshot, prefer_sign_in=prefer_sign_in)
                auth_ready = is_auth_form_ready(
                    snapshot,
                    email=contact.get("email"),
                    password=application_profile.get("apply_account_password"),
                )
                if not auth_ready:
                    filled = await autofill_auth_fields_from_profile(
                        page,
                        snapshot,
                        application_profile,
                        auth_mode=auth_mode,
                    )
                    if filled:
                        await page.wait_for_timeout(800)
                        snapshot = await snapshot_page(page)
                        interactive = count_interactive_fields(snapshot)
                    auth_ready = is_auth_form_ready(
                        snapshot,
                        email=contact.get("email"),
                        password=application_profile.get("apply_account_password"),
                    )

                if auth_ready:
                    auth_mode = resolve_auth_mode(
                        snapshot, prefer_sign_in=prefer_sign_in
                    )
                    result = await submit_auth_and_wait(
                        page,
                        snapshot,
                        auth_mode=auth_mode,
                    )
                    if result == "advanced":
                        auth_stuck_attempts = 0
                        prefer_sign_in = False
                        continue

                    auth_stuck_attempts += 1
                    if result == "account_exists":
                        prefer_sign_in = True
                        await switch_to_sign_in_form(page)
                        await page.wait_for_timeout(1000)
                        continue

                    if auth_stuck_attempts >= _MAX_AUTH_STUCK_ATTEMPTS:
                        logger.info(
                            "Auth submit stuck after %s attempts — human assistance required",
                            auth_stuck_attempts,
                        )
                        if on_human_required is not None:
                            await on_human_required(
                                "auth_blocked: create account / sign in did not advance"
                            )
                        auth_stuck_attempts = 0
                        prefer_sign_in = False
                        continue

                    if auth_stuck_attempts >= 2:
                        prefer_sign_in = True
                        await switch_to_sign_in_form(page)
                        await page.wait_for_timeout(1000)

            signature = snapshot_signature(snapshot)
            if signature == prev_signature:
                stall_steps += 1
            else:
                stall_steps = 0
            prev_signature = signature

            if stall_steps >= _STALL_STEPS:
                if is_likely_login_form(snapshot) and not application_profile.get(
                    "apply_account_password"
                ):
                    return False, "password_required"
                return False, "stalled"

            logger.info(
                "Agent step %s/%s — %s controls (%s fillable inputs)",
                step,
                self.max_steps,
                len(snapshot.fields),
                interactive,
            )

            response = await self._plan_step(
                snapshot=snapshot.model_dump(mode="json"),
                application_profile=application_profile,
                history=history,
            )

            logger.info("Agent thought: %s", response.thought[:200])
            history.append(
                f"step={step} thought={response.thought[:120]} actions={response.actions!r}"
            )

            if response.submit_ready and not self.submit_allowed:
                if can_finish_application(snapshot):
                    logger.info("Form appears ready; dry-run stopping before submit.")
                    return True, "preview_ready"
                logger.info(
                    "Ignoring premature submit_ready (%s inputs) — still navigating.",
                    interactive,
                )

            executed = False
            allowed_selectors = {field.selector for field in snapshot.fields}
            for action in response.actions:
                if action.action == "done":
                    if can_finish_application(snapshot):
                        return True, "preview_ready"
                    logger.info("Ignoring premature done — still on auth/landing page.")
                    continue
                if action.action == "fail":
                    return False, action.reason or "agent_failed"
                if action.action == "need_human":
                    reason = action.reason or "assistance_required"
                    logger.info("Human assistance required: %s", reason)
                    if on_human_required is not None:
                        await on_human_required(reason)
                    executed = True
                    continue
                if action.action == "wait":
                    await page.wait_for_timeout(_WAIT_MS)
                    executed = True
                    continue
                if action.selector and "utilityButtonSignIn" in action.selector:
                    if is_likely_login_form(snapshot):
                        logger.info(
                            "Skipping header Sign In — use the on-page Create Account form."
                        )
                        continue
                if action.selector and action.selector not in allowed_selectors:
                    logger.warning(
                        "Rejected selector not in page snapshot: %s (%s)",
                        action.selector,
                        action.reason,
                    )
                    continue
                if await self._execute_action(page, action, resume_pdf_path):
                    executed = True
                await page.wait_for_timeout(500)

            if response.submit_ready and self.submit_allowed:
                if can_finish_application(snapshot):
                    return True, "submitted"
                logger.info(
                    "Ignoring premature submit_ready — application not complete."
                )

            if not executed and not response.actions:
                logger.warning("Agent returned no actions; stopping.")
                return False, "stalled"

        return False, "max_steps_reached"

    async def _plan_step(
        self,
        *,
        snapshot: dict[str, Any],
        application_profile: dict[str, Any],
        history: list[str],
    ) -> AgentStepResponse:
        user_prompt = {
            "submit_allowed": self.submit_allowed,
            "recent_history": history[-5:],
            "page": snapshot,
            "application_profile": json.loads(
                profile_payload_for_prompt(application_profile)
            ),
            "response_schema": AgentStepResponse.model_json_schema(),
        }
        completion = await acompletion(
            model=self.model,
            temperature=self.temperature,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(user_prompt, indent=2),
                },
            ],
            api_key=self._api_key_for_model(self.model),
            response_format=AgentStepResponse,
        )
        content = completion.choices[0].message.content
        if isinstance(content, str):
            return AgentStepResponse.model_validate_json(content)
        if isinstance(content, dict):
            return AgentStepResponse.model_validate(content)
        raise RuntimeError("Unexpected LLM response format")

    async def _execute_action(
        self,
        page: Page,
        action: BrowserAction,
        resume_pdf_path: Path | None,
    ) -> bool:
        if not action.selector:
            logger.warning("Skipping action without selector: %s", action.action)
            return False

        selector = action.selector
        logger.info("Action %s on %s (%s)", action.action, selector, action.reason)

        try:
            if action.action == "fill":
                return await fill_control(page, selector, action.value or "")
            if action.action == "select":
                await page.select_option(selector, action.value or "", timeout=5000)
                return True
            if action.action == "click":
                return await click_control(page, selector)
            if action.action == "upload" and resume_pdf_path:
                await page.set_input_files(selector, str(resume_pdf_path), timeout=5000)
                return True
        except PlaywrightTimeoutError as exc:
            logger.warning("Action timed out: %s", exc)
        return False
