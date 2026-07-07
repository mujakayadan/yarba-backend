"""Service for owner-facing portfolio chat conversation views."""

from datetime import UTC, datetime, timedelta

from beanie import PydanticObjectId

from api.schemas.portfolio_chat_conversations import (
    PortfolioChatConversationDetailResponse,
    PortfolioChatConversationListResponse,
    PortfolioChatConversationSummary,
    PortfolioChatMessageResponse,
    PortfolioChatStats,
)
from core.exceptions.base import NotFoundException
from core.models.portfolio_chat_conversation import PortfolioChatConversation
from core.repositories.portfolio_chat_conversation_repository import (
    PortfolioChatConversationRepository,
)
from core.repositories.portfolio_website_repository import PortfolioWebsiteRepository


class PortfolioChatConversationService:
    """List and retrieve stored visitor chat conversations."""

    def __init__(
        self,
        conversation_repository: PortfolioChatConversationRepository,
        website_repository: PortfolioWebsiteRepository,
    ) -> None:
        self.conversation_repository = conversation_repository
        self.website_repository = website_repository

    async def list_conversations(
        self,
        user_id: PydanticObjectId,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> PortfolioChatConversationListResponse:
        website = await self.website_repository.get_by_user_id(user_id)
        if not website:
            raise NotFoundException(message="Portfolio website not found")

        conversations, total = await self.conversation_repository.list_for_user(
            user_id, limit=limit, offset=offset
        )
        stats = await self._build_stats(user_id)

        return PortfolioChatConversationListResponse(
            conversations=[
                self._to_summary(conversation) for conversation in conversations
            ],
            total=total,
            stats=stats,
        )

    async def get_conversation(
        self,
        user_id: PydanticObjectId,
        conversation_id: str,
    ) -> PortfolioChatConversationDetailResponse:
        conversation = await self.conversation_repository.get_for_user(
            user_id, conversation_id
        )
        if not conversation:
            raise NotFoundException(message="Conversation not found")

        return PortfolioChatConversationDetailResponse(
            conversation_id=conversation.conversation_id,
            preview=conversation.preview,
            message_count=conversation.message_count,
            calendly_mentioned=conversation.calendly_mentioned,
            started_at=conversation.started_at,
            last_message_at=conversation.last_message_at,
            subdomain=conversation.subdomain,
            user_agent=conversation.metadata.user_agent,
            referrer=conversation.metadata.referrer,
            messages=[
                PortfolioChatMessageResponse(
                    role=message.role,
                    content=message.content,
                    created_at=message.created_at,
                )
                for message in conversation.messages
            ],
        )

    async def _build_stats(self, user_id: PydanticObjectId) -> PortfolioChatStats:
        week_ago = datetime.now(UTC) - timedelta(days=7)
        all_conversations = await PortfolioChatConversation.find(
            PortfolioChatConversation.user_id == user_id
        ).to_list()

        conversations_this_week = sum(
            1 for item in all_conversations if self._as_utc(item.started_at) >= week_ago
        )
        total_messages = sum(item.message_count for item in all_conversations)

        return PortfolioChatStats(
            total_conversations=len(all_conversations),
            conversations_this_week=conversations_this_week,
            total_messages=total_messages,
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _to_summary(
        conversation: PortfolioChatConversation,
    ) -> PortfolioChatConversationSummary:
        return PortfolioChatConversationSummary(
            conversation_id=conversation.conversation_id,
            preview=conversation.preview,
            message_count=conversation.message_count,
            calendly_mentioned=conversation.calendly_mentioned,
            started_at=conversation.started_at,
            last_message_at=conversation.last_message_at,
            subdomain=conversation.subdomain,
        )
