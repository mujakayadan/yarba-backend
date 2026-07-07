"""Schemas for portfolio website chatbot API."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MAX_CHAT_HISTORY = 20
MAX_CHAT_MESSAGE_LENGTH = 2000


class ChatMessage(BaseModel):
    """A single message in chat history."""

    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=MAX_CHAT_MESSAGE_LENGTH)


class PortfolioChatRequest(BaseModel):
    """Request body for portfolio chatbot."""

    subdomain: str = Field(..., min_length=3, max_length=63)
    message: str = Field(..., min_length=1, max_length=MAX_CHAT_MESSAGE_LENGTH)
    conversation_id: str | None = None
    history: list[ChatMessage] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class PortfolioChatResponse(BaseModel):
    """Response from portfolio chatbot."""

    response: str
    conversation_id: str
