"""Repository for stored portfolio chat conversations."""

from datetime import UTC, datetime, timedelta

from beanie import PydanticObjectId, SortDirection

from core.models.portfolio_chat_conversation import (
    CONVERSATION_RETENTION_DAYS,
    MAX_STORED_MESSAGES,
    PREVIEW_MAX_LENGTH,
    PortfolioChatConversation,
    PortfolioChatMessageEntry,
    PortfolioChatVisitorMetadata,
)


class PortfolioChatConversationRepository:
    """Persistence helpers for portfolio chat conversations."""

    async def get_by_conversation_id(
        self, conversation_id: str
    ) -> PortfolioChatConversation | None:
        return await PortfolioChatConversation.find_one(
            PortfolioChatConversation.conversation_id == conversation_id
        )

    async def list_for_user(
        self,
        user_id: PydanticObjectId,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[PortfolioChatConversation], int]:
        query = PortfolioChatConversation.find(
            PortfolioChatConversation.user_id == user_id
        ).sort([("last_message_at", SortDirection.DESCENDING)])

        total = await query.count()
        items = await query.skip(offset).limit(limit).to_list()
        return items, total

    async def get_for_user(
        self,
        user_id: PydanticObjectId,
        conversation_id: str,
    ) -> PortfolioChatConversation | None:
        return await PortfolioChatConversation.find_one(
            PortfolioChatConversation.user_id == user_id,
            PortfolioChatConversation.conversation_id == conversation_id,
        )

    async def delete_by_website_id(self, website_id: PydanticObjectId) -> int:
        result = await PortfolioChatConversation.find(
            PortfolioChatConversation.website_id == website_id
        ).delete()
        return int(result.deleted_count if result else 0)

    async def append_exchange(
        self,
        *,
        conversation_id: str,
        user_id: PydanticObjectId,
        website_id: PydanticObjectId,
        portfolio_id: PydanticObjectId,
        subdomain: str,
        user_message: str,
        assistant_message: str,
        visitor_metadata: PortfolioChatVisitorMetadata | None = None,
        calendly_mentioned: bool = False,
    ) -> PortfolioChatConversation:
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=CONVERSATION_RETENTION_DAYS)
        conversation = await self.get_by_conversation_id(conversation_id)

        user_entry = PortfolioChatMessageEntry(
            role="user", content=user_message, created_at=now
        )
        assistant_entry = PortfolioChatMessageEntry(
            role="assistant", content=assistant_message, created_at=now
        )

        if conversation is None:
            preview = user_message.strip()
            if len(preview) > PREVIEW_MAX_LENGTH:
                preview = preview[: PREVIEW_MAX_LENGTH - 3] + "..."

            conversation = PortfolioChatConversation(
                conversation_id=conversation_id,
                user_id=user_id,
                website_id=website_id,
                portfolio_id=portfolio_id,
                subdomain=subdomain,
                started_at=now,
                last_message_at=now,
                expires_at=expires_at,
                message_count=2,
                preview=preview,
                calendly_mentioned=calendly_mentioned,
                metadata=visitor_metadata or PortfolioChatVisitorMetadata(),
                messages=[user_entry, assistant_entry],
            )
            await conversation.insert()
            return conversation

        conversation.messages.extend([user_entry, assistant_entry])
        if len(conversation.messages) > MAX_STORED_MESSAGES:
            conversation.messages = conversation.messages[-MAX_STORED_MESSAGES:]

        conversation.message_count = len(conversation.messages)
        conversation.last_message_at = now
        conversation.expires_at = expires_at
        if calendly_mentioned:
            conversation.calendly_mentioned = True
        if visitor_metadata and not conversation.metadata.user_agent:
            conversation.metadata = visitor_metadata

        await conversation.save()
        return conversation
