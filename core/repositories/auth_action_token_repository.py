"""Repository for single-use authentication action tokens."""

from datetime import datetime
from typing import Any, cast

from beanie import PydanticObjectId
from pymongo import ReturnDocument

from core.models.auth_action_token import AuthActionPurpose, AuthActionToken

from .base_repository import BeanieRepository


class AuthActionTokenRepository(BeanieRepository[AuthActionToken]):
    """Create and atomically consume password and verification tokens."""

    def __init__(self) -> None:
        super().__init__(AuthActionToken)

    async def supersede_active(
        self,
        *,
        user_id: PydanticObjectId,
        purpose: AuthActionPurpose,
        now: datetime,
    ) -> None:
        """Invalidate outstanding tokens for the same user and purpose."""
        collection = AuthActionToken.get_pymongo_collection()
        await collection.update_many(
            {
                "user_id": user_id,
                "purpose": purpose,
                "consumed_at": None,
            },
            {"$set": {"consumed_at": now}},
        )

    async def consume(
        self,
        *,
        token_hash: str,
        purpose: AuthActionPurpose,
        now: datetime,
    ) -> AuthActionToken | None:
        """Consume a valid token exactly once using compare-and-set."""
        collection = AuthActionToken.get_pymongo_collection()
        document: dict[str, Any] | None = await collection.find_one_and_update(
            {
                "token_hash": token_hash,
                "purpose": purpose,
                "consumed_at": None,
                "expires_at": {"$gt": now},
            },
            {"$set": {"consumed_at": now}},
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            return None
        return cast(AuthActionToken, AuthActionToken.model_validate(document))
