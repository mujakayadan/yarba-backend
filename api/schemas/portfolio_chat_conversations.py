"""Schemas for portfolio chat conversation owner API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PortfolioChatMessageResponse(BaseModel):
    """A message in a stored conversation."""

    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PortfolioChatConversationSummary(BaseModel):
    """Summary row for conversation list."""

    conversation_id: str
    preview: str
    message_count: int
    calendly_mentioned: bool
    started_at: datetime
    last_message_at: datetime
    subdomain: str


class PortfolioChatStats(BaseModel):
    """Aggregate chat metrics for the owner dashboard."""

    total_conversations: int
    conversations_this_week: int
    total_messages: int


class PortfolioChatConversationListResponse(BaseModel):
    """Paginated conversation list with stats."""

    conversations: list[PortfolioChatConversationSummary]
    total: int
    stats: PortfolioChatStats


class PortfolioChatConversationDetailResponse(BaseModel):
    """Full conversation transcript for owner review."""

    conversation_id: str
    preview: str
    message_count: int
    calendly_mentioned: bool
    started_at: datetime
    last_message_at: datetime
    subdomain: str
    user_agent: str | None = None
    referrer: str | None = None
    messages: list[PortfolioChatMessageResponse]
