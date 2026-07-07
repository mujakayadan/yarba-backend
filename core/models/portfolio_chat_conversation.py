"""Stored portfolio chatbot conversations for owner review."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import IndexModel

from core.models.document_config import BSON_DATETIME_ENCODERS, NESTED_MODEL_CONFIG

CONVERSATION_RETENTION_DAYS = 90
MAX_STORED_MESSAGES = 100
PREVIEW_MAX_LENGTH = 120


class PortfolioChatMessageEntry(BaseModel):
    """A single message in a stored conversation."""

    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=4000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = NESTED_MODEL_CONFIG


class PortfolioChatVisitorMetadata(BaseModel):
    """Non-sensitive visitor metadata captured on first message."""

    user_agent: str | None = Field(default=None, max_length=512)
    referrer: str | None = Field(default=None, max_length=2048)

    model_config = NESTED_MODEL_CONFIG


class PortfolioChatConversation(Document):
    """Visitor chat session for a published portfolio website."""

    conversation_id: Annotated[str, Indexed()] = Field(
        description="Public session id returned to the chat widget"
    )
    user_id: PydanticObjectId = Field(description="Portfolio owner user id")
    website_id: PydanticObjectId
    portfolio_id: PydanticObjectId
    subdomain: str

    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_message_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime = Field(
        description="TTL anchor; document removed after this instant"
    )
    message_count: int = Field(default=0, ge=0)
    preview: str = Field(
        default="",
        max_length=PREVIEW_MAX_LENGTH,
        description="Truncated first visitor message for list views",
    )
    calendly_mentioned: bool = Field(default=False)
    metadata: PortfolioChatVisitorMetadata = Field(
        default_factory=PortfolioChatVisitorMetadata
    )
    messages: list[PortfolioChatMessageEntry] = Field(default_factory=list)

    class Settings:
        name = "portfolio_chat_conversations"
        indexes = [
            "conversation_id",
            "user_id",
            "website_id",
            [("user_id", -1), ("last_message_at", -1)],
            IndexModel([("expires_at", 1)], expireAfterSeconds=0),
        ]
        bson_encoders = BSON_DATETIME_ENCODERS
