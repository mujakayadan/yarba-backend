"""Human-in-the-loop prompts for the apply CLI."""

from __future__ import annotations

HUMAN_REASON_HINTS: dict[str, str] = {
    "captcha": "Solve the CAPTCHA in the browser window.",
    "email_verification": "Complete email verification (code or link) in the browser.",
    "sms_verification": "Enter the SMS verification code in the browser.",
    "missing_profile_data": (
        "Add the missing information in yarba.app → Profile → Application Settings, "
        "then continue."
    ),
    "auth_blocked": (
        "Complete sign-in or account creation in the browser "
        "(wrong password, existing account, or employer verification)."
    ),
}


def human_assistance_message(reason: str) -> str:
    """User-facing instruction for a need_human reason."""
    key = reason.split(":", 1)[0].strip().lower()
    hint = HUMAN_REASON_HINTS.get(key)
    if hint:
        return f"{hint} ({reason})"
    return reason or "Complete the required step in the browser."
