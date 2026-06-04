"""Tests for inbound email webhooks."""

import json
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from httpx import AsyncClient

from core.models.inbound_email import InboundEmail


@pytest.fixture
def enable_email_webhook(monkeypatch: pytest.MonkeyPatch) -> None:
    from config.settings import settings

    monkeypatch.setattr(settings.features, "enable_email_to_resume", True)


@pytest.mark.asyncio
async def test_resend_webhook_disabled_returns_404(async_client: AsyncClient):
    payload = {
        "type": "email.received",
        "data": {
            "email_id": "email-123",
            "from": "user@example.com",
            "to": ["inbound@resend.dev"],
            "subject": "Job posting",
        },
    }
    response = await async_client.post(
        "/api/v1/webhooks/resend",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_resend_webhook_accepts_email_received(
    async_client: AsyncClient,
    enable_email_webhook: None,
    monkeypatch: pytest.MonkeyPatch,
):
    captured: list[str] = []

    async def fake_job(email_id: str) -> None:
        captured.append(email_id)

    monkeypatch.setattr(
        "api.routers.webhooks._run_inbound_email_job",
        fake_job,
    )

    payload = {
        "type": "email.received",
        "data": {
            "email_id": "email-abc-123",
            "from": "user@example.com",
            "to": ["inbound@resend.dev"],
            "subject": "Senior Engineer role",
        },
    }
    response = await async_client.post(
        "/api/v1/webhooks/resend",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "accepted"
    assert captured == ["email-abc-123"]


@pytest.mark.asyncio
async def test_resend_webhook_ignores_other_events(
    async_client: AsyncClient,
    enable_email_webhook: None,
):
    payload = {"type": "email.sent", "data": {"email_id": "email-123"}}
    response = await async_client.post(
        "/api/v1/webhooks/resend",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "ignored"


@pytest.mark.asyncio
async def test_email_resume_service_skips_duplicate(
    beanie_db,
    enable_email_webhook: None,
):
    from core.services.email_resume_service import EmailResumeService

    mock_resend = AsyncMock()
    mock_resend.get_received_email = AsyncMock()

    service = EmailResumeService(
        user_repository=AsyncMock(),
        profile_service=AsyncMock(),
        portfolio_service=AsyncMock(),
        resume_service=AsyncMock(),
        resume_generation_service=AsyncMock(),
        resend_client=mock_resend,
    )

    assert await service.claim_inbound_email("dup-id", "user@example.com") is True
    assert await service.claim_inbound_email("dup-id", "user@example.com") is False

    await service.process_inbound_email("dup-id")
    mock_resend.get_received_email.assert_not_called()

    record = await InboundEmail.find_one(InboundEmail.email_id == "dup-id")
    assert record is not None
