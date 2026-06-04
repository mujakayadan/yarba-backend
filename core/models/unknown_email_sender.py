"""Track unknown senders who were sent a one-time registration CTA."""

from datetime import UTC, datetime
from typing import Annotated

from beanie import Document, Indexed
from pydantic import Field

from core.models.document_config import DOCUMENT_MODEL_CONFIG


class UnknownEmailSender(Document):
    """Sender address that received the register-by-email CTA at most once."""

    sender_email: Annotated[str, Indexed(unique=True)]
    notified_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = DOCUMENT_MODEL_CONFIG

    class Settings:
        name = "unknown_email_senders"
