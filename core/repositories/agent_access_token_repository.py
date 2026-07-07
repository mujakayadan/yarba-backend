"""Repository for agent access tokens."""

from beanie import PydanticObjectId

from core.models.agent_access_token import AgentAccessToken
from core.utils.agent_access_token import hash_token

from .base_repository import BeanieRepository


class AgentAccessTokenRepository(BeanieRepository[AgentAccessToken]):
    """Repository for AgentAccessToken documents."""

    def __init__(self) -> None:
        super().__init__(AgentAccessToken)

    async def get_active_by_raw_token(self, raw_token: str) -> AgentAccessToken | None:
        """Find an active token record by raw token value."""
        token_hash = hash_token(raw_token)
        return await AgentAccessToken.find_one(
            {"token_hash": token_hash, "is_active": True}
        )

    async def list_by_user(self, user_id: PydanticObjectId) -> list[AgentAccessToken]:
        """List all tokens for a user."""
        return await AgentAccessToken.find({"user_id": user_id}).to_list()

    async def touch_last_used(self, token_id: PydanticObjectId) -> None:
        """Update last_used_at for audit."""
        from datetime import UTC, datetime

        token = await AgentAccessToken.get(token_id)
        if token:
            token.last_used_at = datetime.now(UTC)
            token.updated_at = datetime.now(UTC)
            await token.save()
