"""Tests for shared Resend sender and email presentation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config.settings import ResendSettings
from core.services.email_clients.resend_client import ResendClient


def test_resend_settings_use_purpose_specific_sender_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RESEND__FROM", raising=False)
    monkeypatch.delenv("RESEND__RESUME_FROM", raising=False)

    resend = ResendSettings(_env_file=None)

    assert resend.from_address == "noreply@yarba.app"
    assert resend.resume_from_address == "resumes@yarba.app"


@pytest.mark.asyncio
async def test_send_email_applies_brand_theme_and_footer() -> None:
    response = AsyncMock()
    response.status = 200
    response.__aenter__.return_value = response
    session = AsyncMock()
    session.__aenter__.return_value = session
    session.post = MagicMock(return_value=response)
    client = ResendClient(
        api_key="re_test",
        from_address="noreply@yarba.app",
    )

    with patch(
        "core.services.email_clients.resend_client.aiohttp.ClientSession",
        return_value=session,
    ):
        await client.send_email(
            to="user@example.com",
            subject="Account activity",
            text="Something happened in your account.",
        )

    payload = session.post.call_args.kwargs["json"]
    assert payload["from"] == "noreply@yarba.app"
    assert "YARBA | Your career, tailored." in payload["text"]
    assert "Something happened in your account." in payload["html"]
    assert "background:#112D4E" in payload["html"]
    assert "This service email was sent" in payload["html"]
