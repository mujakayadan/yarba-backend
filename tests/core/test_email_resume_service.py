"""Tests for email-to-resume orchestration."""

from unittest.mock import AsyncMock

import pytest

from core.models.inbound_email import InboundEmail
from core.models.unknown_email_sender import UnknownEmailSender
from core.schemas.resend_schemas import ResendReceivedEmail
from core.services.email_resume_service import EmailResumeService


def _build_service(*, user_repository: AsyncMock | None = None) -> EmailResumeService:
    mock_resend = AsyncMock()
    mock_resend.get_received_email = AsyncMock(
        return_value=ResendReceivedEmail(
            id="email-1",
            **{
                "from": "stranger@example.com",
                "to": ["jobs@resend.dev"],
                "subject": "Fwd: Software Engineer",
                "text": "x" * 120,
            },
        )
    )
    return EmailResumeService(
        user_repository=user_repository or AsyncMock(),
        profile_service=AsyncMock(),
        portfolio_service=AsyncMock(),
        resume_service=AsyncMock(),
        resume_generation_service=AsyncMock(),
        resend_client=mock_resend,
    )


@pytest.mark.asyncio
async def test_unknown_sender_gets_one_time_register_cta(beanie_db):
    user_repo = AsyncMock()
    user_repo.get_by_email_insensitive = AsyncMock(return_value=None)
    service = _build_service(user_repository=user_repo)

    await service.process_inbound_email("email-1")

    service.resend_client.send_email.assert_awaited_once()
    call_kwargs = service.resend_client.send_email.await_args.kwargs
    assert call_kwargs["to"] == "stranger@example.com"
    assert "/register" in call_kwargs["text"]
    assert "Create your YARBA account" in call_kwargs["subject"]

    record = await InboundEmail.find_one(InboundEmail.email_id == "email-1")
    assert record is not None
    assert record.status == "unknown_sender"

    unknown = await UnknownEmailSender.find_one(
        UnknownEmailSender.sender_email == "stranger@example.com"
    )
    assert unknown is not None


@pytest.mark.asyncio
async def test_repeat_unknown_sender_is_silent(beanie_db):
    await UnknownEmailSender(sender_email="stranger@example.com").insert()

    user_repo = AsyncMock()
    user_repo.get_by_email_insensitive = AsyncMock(return_value=None)
    service = _build_service(user_repository=user_repo)
    mock_resend = service.resend_client
    mock_resend.get_received_email = AsyncMock(
        return_value=ResendReceivedEmail(
            id="email-2",
            **{
                "from": "stranger@example.com",
                "to": ["jobs@resend.dev"],
                "subject": "Another job",
                "text": "y" * 120,
            },
        )
    )

    await service.process_inbound_email("email-2")

    mock_resend.send_email.assert_not_awaited()
    record = await InboundEmail.find_one(InboundEmail.email_id == "email-2")
    assert record is not None
    assert record.status == "unknown_sender"


@pytest.mark.asyncio
async def test_unknown_sender_skips_resume_generation(beanie_db):
    user_repo = AsyncMock()
    user_repo.get_by_email_insensitive = AsyncMock(return_value=None)
    service = _build_service(user_repository=user_repo)

    await service.process_inbound_email("email-1")

    service.resume_service.create_resume.assert_not_awaited()
    service.resume_generation_service.generate_resume_textual_content.assert_not_awaited()
