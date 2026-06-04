"""Inbound email tracking for idempotent webhook processing."""

from datetime import UTC, datetime
from typing import Annotated

from beanie import Document, Indexed
from pydantic import Field

from core.models.document_config import DOCUMENT_MODEL_CONFIG


class InboundEmail(Document):
    """Record of a processed inbound email to prevent duplicate resume generation."""

    email_id: Annotated[str, Indexed(unique=True)]
    sender_email: str = Field(default="", description="Normalized sender email")
    status: str = Field(
        default="accepted",
        description="Processing status: accepted, completed, failed",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = DOCUMENT_MODEL_CONFIG

    class Settings:
        name = "inbound_emails"
