"""Pydantic schemas for Resend webhook and API payloads."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ResendEmailReceivedData(BaseModel):
    """Payload data for ``email.received`` events."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    email_id: str
    from_: str = Field(default="", alias="from")
    to: list[str] = Field(default_factory=list)
    subject: str = ""
    message_id: str | None = None


class ResendWebhookEvent(BaseModel):
    """Top-level Resend webhook event."""

    model_config = ConfigDict(extra="ignore")

    type: str
    created_at: str | None = None
    data: ResendEmailReceivedData


class ResendReceivedEmail(BaseModel):
    """Full received email returned by the Resend Receiving API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    from_: str = Field(alias="from")
    to: list[str] = Field(default_factory=list)
    subject: str = ""
    text: str | None = None
    html: str | None = None
    headers: dict[str, Any] = Field(default_factory=dict)
    message_id: str | None = None
