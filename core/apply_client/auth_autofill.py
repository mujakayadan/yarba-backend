"""Fill sign-in / sign-up fields from application profile data (generic label matching)."""

from __future__ import annotations

from typing import Any, Literal

from playwright.async_api import Page

from config.logging_config import get_logger
from core.apply_client.browser_interactions import (
    click_button_by_role,
    click_control,
    click_locator,
    fill_control,
)
from core.apply_client.page_navigation import (
    auth_indicates_existing_account,
    auth_submit_progressed,
    is_create_account_form,
)
from core.apply_client.page_snapshot import snapshot_page
from core.apply_client.schemas import FormFieldSnapshot, PageSnapshot

logger = get_logger(__name__)

AuthMode = Literal["create", "sign_in"]
AuthSubmitResult = Literal["advanced", "stuck", "account_exists"]

_AUTH_SKIP_LABELS = ("forgot", "linkedin", "sign in with", "back", "cancel")
_HEADER_SIGN_IN_MARKERS = ("utilitybuttonsignin",)
_CREATE_ACCOUNT_ROLE_NAMES = ("Create Account", "Register", "Sign up")
_SIGN_IN_ROLE_NAMES = ("Sign In", "Log In")
_CREATE_ACCOUNT_SELECTORS = ('[data-automation-id="createAccountSubmitButton"]',)
_SIGN_IN_SELECTORS = ('[data-automation-id="signInSubmitButton"]',)
_SIGN_IN_TAB_SELECTORS = (
    '[data-automation-id="signInLink"]',
    '[data-automation-id="signInTab"]',
)
_AUTH_FORM_SELECTORS = (
    '[data-automation-id="createAccountForm"]',
    '[data-automation-id="signInFormo"]',
    '[data-automation-id="signInForm"]',
)


def resolve_auth_mode(snapshot: PageSnapshot, *, prefer_sign_in: bool) -> AuthMode:
    """Pick create vs sign-in submit path for the current auth pane."""
    if prefer_sign_in:
        return "sign_in"
    if is_create_account_form(snapshot):
        return "create"
    return "sign_in"


def _field_text(field: FormFieldSnapshot) -> str:
    parts = (
        field.label or "",
        field.placeholder or "",
        field.name or "",
        field.field_id or "",
    )
    return " ".join(parts).lower()


def _is_email_field(field: FormFieldSnapshot) -> bool:
    text = _field_text(field)
    return field.input_type == "email" or "email" in text


def _is_password_field(field: FormFieldSnapshot) -> bool:
    return field.input_type == "password" or "password" in _field_text(field)


def _is_honeypot_field(field: FormFieldSnapshot) -> bool:
    text = _field_text(field)
    return any(
        token in text for token in ("honeypot", "bot", "leave blank", "do not fill")
    )


def _is_create_submit_field(field: FormFieldSnapshot) -> bool:
    label = (field.label or "").lower()
    selector_lower = field.selector.lower()
    return (
        "createaccountsubmitbutton" in selector_lower
        or "create account" in label
        or "register" in label
    )


def _is_sign_in_submit_field(field: FormFieldSnapshot) -> bool:
    label = (field.label or "").lower()
    selector_lower = field.selector.lower()
    return (
        "signinsubmitbutton" in selector_lower
        or "sign in" in label
        or "log in" in label
    )


async def autofill_auth_fields_from_profile(
    page: Page,
    snapshot: PageSnapshot,
    application_profile: dict[str, Any],
    *,
    auth_mode: AuthMode,
) -> int:
    """Fill empty email/password inputs on auth screens using profile data."""
    email = (application_profile.get("contact") or {}).get("email")
    password = application_profile.get("apply_account_password")
    filled = 0

    for field in snapshot.fields:
        if field.tag != "input":
            continue
        if _is_honeypot_field(field):
            continue

        if auth_mode == "sign_in" and _is_verify_password_field(field):
            continue

        if email and _is_email_field(field):
            current = (field.value or "").strip()
            if current == email or current:
                continue
            if await fill_control(page, field.selector, email):
                logger.info("Filled email on auth form")
                filled += 1
            continue

        if password and _is_password_field(field):
            if auth_mode == "sign_in" and _is_verify_password_field(field):
                continue
            current = (field.value or "").strip()
            if current:
                continue
            if await fill_control(page, field.selector, password):
                logger.info(
                    "Filled password field on auth form (%s)",
                    field.label or field.selector,
                )
                filled += 1

    return filled


def _is_verify_password_field(field: FormFieldSnapshot) -> bool:
    text = _field_text(field)
    return field.input_type == "password" and any(
        token in text for token in ("verify", "confirm", "re-enter", "reenter")
    )


def pick_auth_submit_field(
    snapshot: PageSnapshot,
    *,
    auth_mode: AuthMode,
) -> FormFieldSnapshot | None:
    """Return the auth submit button for the active create/sign-in mode."""
    for field in snapshot.fields:
        if field.tag != "button" and field.input_type not in {"submit", "button"}:
            continue
        label = (field.label or "").lower()
        selector_lower = field.selector.lower()
        if any(skip in label for skip in _AUTH_SKIP_LABELS):
            continue
        if any(marker in selector_lower for marker in _HEADER_SIGN_IN_MARKERS):
            continue
        if auth_mode == "create" and _is_create_submit_field(field):
            return field
        if auth_mode == "sign_in" and _is_sign_in_submit_field(field):
            return field
    return None


async def _submit_via_selectors(page: Page, *, auth_mode: AuthMode) -> bool:
    selectors = (
        _CREATE_ACCOUNT_SELECTORS if auth_mode == "create" else _SIGN_IN_SELECTORS
    )
    for selector in selectors:
        logger.info("Trying auth submit selector %s", selector)
        if await click_control(page, selector):
            return True
    return False


async def _submit_via_role_scoped(page: Page, *, auth_mode: AuthMode) -> bool:
    role_names = (
        _CREATE_ACCOUNT_ROLE_NAMES if auth_mode == "create" else _SIGN_IN_ROLE_NAMES
    )
    logger.info(
        "Trying scoped role-based auth submit (%s)",
        ", ".join(role_names),
    )
    for form_selector in _AUTH_FORM_SELECTORS:
        form = page.locator(form_selector)
        if await form.count() == 0:
            continue
        for name in role_names:
            button = form.first.get_by_role("button", name=name)
            count = await button.count()
            for index in range(count):
                candidate = button.nth(index)
                if await click_locator(candidate, label=f"{form_selector}:{name}"):
                    return True
    return await click_button_by_role(page, role_names)


async def try_submit_auth_form(
    page: Page,
    snapshot: PageSnapshot,
    *,
    auth_mode: AuthMode,
) -> bool:
    """Click the primary auth submit button for the active mode."""
    field = pick_auth_submit_field(snapshot, auth_mode=auth_mode)
    if field is not None:
        logger.info(
            "Submitting auth form (%s mode) via %s",
            auth_mode,
            field.label or field.selector,
        )
        if await click_control(page, field.selector):
            return True

    if await _submit_via_selectors(page, auth_mode=auth_mode):
        return True
    return await _submit_via_role_scoped(page, auth_mode=auth_mode)


async def switch_to_sign_in_form(page: Page) -> bool:
    """Open the sign-in pane when create-account is blocked."""
    for selector in _SIGN_IN_TAB_SELECTORS:
        if await click_control(page, selector):
            logger.info("Switched auth pane via %s", selector)
            await page.wait_for_timeout(1000)
            return True
    return False


async def submit_auth_and_wait(
    page: Page,
    snapshot: PageSnapshot,
    *,
    auth_mode: AuthMode,
) -> AuthSubmitResult:
    """Submit auth and report whether the flow advanced."""
    clicked = await try_submit_auth_form(page, snapshot, auth_mode=auth_mode)
    if not clicked:
        logger.warning("Auth submit click did not succeed (%s mode)", auth_mode)
        return "stuck"

    await page.wait_for_timeout(2500)
    after = await snapshot_page(page)

    if auth_indicates_existing_account(after):
        logger.info("Auth page indicates account already exists")
        return "account_exists"
    if auth_submit_progressed(snapshot, after):
        logger.info("Auth submit advanced the application flow")
        return "advanced"

    logger.warning("Auth submit clicked but page did not advance (%s mode)", auth_mode)
    return "stuck"
