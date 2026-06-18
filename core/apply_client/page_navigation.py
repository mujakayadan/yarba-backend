"""Passive helpers for interpreting page snapshots (no hardcoded clicking)."""

from __future__ import annotations

from core.apply_client.schemas import PageSnapshot


def count_interactive_fields(snapshot: PageSnapshot) -> int:
    """Count inputs the agent can fill (not buttons/hidden/submit)."""
    skip_types = {"hidden", "submit", "button", "image", "reset"}
    count = 0
    for field in snapshot.fields:
        if field.tag not in {"input", "textarea", "select"}:
            continue
        if field.input_type in skip_types:
            continue
        count += 1
    return count


def is_likely_login_form(snapshot: PageSnapshot) -> bool:
    labels = " ".join((field.label or "") for field in snapshot.fields).lower()
    has_password = any(
        field.input_type == "password"
        or "password" in (field.name or "").lower()
        or "password" in (field.field_id or "").lower()
        for field in snapshot.fields
    )
    has_email = any(
        field.input_type == "email"
        or "email" in (field.name or "").lower()
        or "email" in (field.label or "").lower()
        for field in snapshot.fields
    )
    auth_words = ("sign in", "log in", "create account", "register", "password")
    return has_password or (has_email and any(word in labels for word in auth_words))


def count_action_buttons(snapshot: PageSnapshot) -> int:
    return sum(
        1
        for field in snapshot.fields
        if field.tag == "button"
        or field.input_type in {"button", "submit"}
        or (field.tag == "a" and field.label)
    )


MIN_APPLICATION_INPUTS = 5


def is_create_account_form(snapshot: PageSnapshot) -> bool:
    labels = " ".join((field.label or "") for field in snapshot.fields).lower()
    has_verify = any(
        "verify" in (field.label or "").lower()
        or "confirm" in (field.label or "").lower()
        for field in snapshot.fields
        if field.input_type == "password"
    )
    return has_verify or "verify new password" in labels or "create account" in labels


def is_auth_form_ready(
    snapshot: PageSnapshot,
    *,
    email: str | None,
    password: str | None,
) -> bool:
    """True when visible auth inputs appear filled and ready to submit."""
    if not password:
        return False

    password_fields = [
        field
        for field in snapshot.fields
        if field.tag == "input"
        and (
            field.input_type == "password" or "password" in (field.label or "").lower()
        )
    ]
    if not password_fields:
        return False
    if not all((field.value or "").strip() for field in password_fields):
        return False

    if not email:
        return True

    for field in snapshot.fields:
        if field.tag != "input":
            continue
        text = " ".join(
            part
            for part in (field.label, field.placeholder, field.name, field.field_id)
            if part
        ).lower()
        if "email" not in text and field.input_type != "email":
            continue
        if (field.value or "").strip():
            return True
    return False


def can_finish_application(snapshot: PageSnapshot) -> bool:
    """True when the page looks like a filled application, not auth/landing."""
    if is_likely_login_form(snapshot):
        return False
    return count_interactive_fields(snapshot) >= MIN_APPLICATION_INPUTS


def page_text(snapshot: PageSnapshot) -> str:
    """Lowercased visible text derived from snapshot fields."""
    parts = [snapshot.title or ""]
    for field in snapshot.fields:
        for part in (field.label, field.placeholder, field.value):
            if part:
                parts.append(part)
    return " ".join(parts).lower()


_ACCOUNT_EXISTS_MARKERS = (
    "already exists",
    "already registered",
    "account exists",
    "email address is already",
    "sign in instead",
    "use sign in",
)

_VERIFICATION_MARKERS = (
    "verify your email",
    "verification code",
    "check your email",
    "enter the code",
    "confirm your email",
    "email verification",
)


def is_email_verification_page(snapshot: PageSnapshot) -> bool:
    text = page_text(snapshot)
    return any(marker in text for marker in _VERIFICATION_MARKERS)


def auth_indicates_existing_account(snapshot: PageSnapshot) -> bool:
    text = page_text(snapshot)
    return any(marker in text for marker in _ACCOUNT_EXISTS_MARKERS)


def auth_submit_progressed(
    _before: PageSnapshot,
    after: PageSnapshot,
) -> bool:
    """True when auth submit left the login/create-account flow."""
    if is_email_verification_page(after):
        return True
    if is_likely_login_form(after):
        return False
    return True
