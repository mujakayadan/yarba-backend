"""Resend API client for inbound fetch and outbound send."""

import base64
from typing import Any

import aiohttp

from config.logging_config import get_logger
from config.settings import settings
from core.schemas.resend_schemas import ResendReceivedEmail

logger = get_logger(__name__)

RESEND_API_BASE = "https://api.resend.com"


class ResendClient:
    """Client for Resend receiving and sending APIs."""

    def __init__(self, api_key: str, from_address: str) -> None:
        self.api_key = api_key
        self.from_address = from_address

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def get_received_email(self, email_id: str) -> ResendReceivedEmail:
        """Fetch full received email content by ID."""
        url = f"{RESEND_API_BASE}/emails/receiving/{email_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self._headers()) as response:
                if response.status != 200:
                    body = await response.text()
                    msg = f"Resend receiving API error {response.status}: {body}"
                    raise RuntimeError(msg)
                data: dict[str, Any] = await response.json()
        return ResendReceivedEmail.model_validate(data)

    async def send_email(
        self,
        to: str,
        subject: str,
        text: str,
        *,
        html: str | None = None,
        attachments: list[dict[str, str]] | None = None,
    ) -> None:
        """Send an outbound email, optionally with attachments."""
        payload: dict[str, Any] = {
            "from": self.from_address,
            "to": [to],
            "subject": subject,
            "text": text,
        }
        if html:
            payload["html"] = html
        if attachments:
            payload["attachments"] = attachments

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{RESEND_API_BASE}/emails",
                headers=self._headers(),
                json=payload,
            ) as response:
                if response.status not in (200, 201):
                    body = await response.text()
                    msg = f"Resend send API error {response.status}: {body}"
                    raise RuntimeError(msg)

    async def send_pdf_attachment(
        self,
        to: str,
        subject: str,
        text: str,
        pdf_bytes: bytes,
        filename: str = "resume.pdf",
    ) -> None:
        """Send an email with a PDF attachment."""
        await self.send_email(
            to=to,
            subject=subject,
            text=text,
            attachments=[
                {
                    "filename": filename,
                    "content": base64.b64encode(pdf_bytes).decode("ascii"),
                }
            ],
        )


def get_resend_client() -> ResendClient:
    """Build a Resend client from application settings."""
    api_key = settings.resend.api_key.get_secret_value()
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not configured")
    return ResendClient(api_key=api_key, from_address=settings.resend.from_address)
