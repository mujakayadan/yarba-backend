"""Repository for atomic refresh-token session state changes."""

from datetime import datetime
from typing import Any, cast

from beanie import PydanticObjectId
from pymongo import ReturnDocument

from core.models.refresh_token_session import RefreshTokenSession

from .base_repository import BeanieRepository


class RefreshTokenSessionRepository(BeanieRepository[RefreshTokenSession]):
    """Persist refresh-token families and rotate their hashes atomically."""

    def __init__(self) -> None:
        super().__init__(RefreshTokenSession)

    @staticmethod
    def _from_document(document: dict[str, Any] | None) -> RefreshTokenSession | None:
        if document is None:
            return None
        return cast(
            RefreshTokenSession,
            RefreshTokenSession.model_validate(document),
        )

    async def get_by_token_hash(self, token_hash: str) -> RefreshTokenSession | None:
        """Find a session by its current token hash."""
        return await RefreshTokenSession.find_one({"token_hash": token_hash})

    async def get_by_family_id(self, family_id: str) -> RefreshTokenSession | None:
        """Find a session by refresh-token family ID."""
        return await RefreshTokenSession.find_one({"family_id": family_id})

    async def rotate_current_hash(
        self,
        *,
        current_hash: str,
        replacement_hash: str,
        now: datetime,
    ) -> RefreshTokenSession | None:
        """Replace an active hash without extending the family's expiration."""
        collection = RefreshTokenSession.get_pymongo_collection()
        document = await collection.find_one_and_update(
            {
                "token_hash": current_hash,
                "revoked_at": None,
                "expires_at": {"$gt": now},
            },
            {
                "$set": {
                    "token_hash": replacement_hash,
                    "last_used_at": now,
                    "last_rotated_at": now,
                    "updated_at": now,
                },
                "$push": {"used_token_hashes": current_hash},
                "$inc": {"rotation_count": 1},
            },
            return_document=ReturnDocument.AFTER,
        )
        return self._from_document(document)

    async def revoke_reused_family(
        self,
        *,
        reused_hash: str,
        now: datetime,
    ) -> RefreshTokenSession | None:
        """Atomically mark a family revoked when an old hash is presented again."""
        collection = RefreshTokenSession.get_pymongo_collection()
        document = await collection.find_one_and_update(
            {
                "used_token_hashes": reused_hash,
                "revoked_at": None,
            },
            {
                "$set": {
                    "revoked_at": now,
                    "reuse_detected_at": now,
                    "revocation_reason": "refresh_token_reuse",
                    "updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return self._from_document(document)

    async def revoke_family(
        self,
        *,
        family_id: str,
        reason: str,
        now: datetime,
    ) -> RefreshTokenSession | None:
        """Revoke an active refresh-token family."""
        collection = RefreshTokenSession.get_pymongo_collection()
        document = await collection.find_one_and_update(
            {"family_id": family_id, "revoked_at": None},
            {
                "$set": {
                    "revoked_at": now,
                    "revocation_reason": reason,
                    "updated_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return self._from_document(document)

    async def revoke_all_for_user(
        self,
        *,
        user_id: PydanticObjectId,
        reason: str,
        now: datetime,
    ) -> int:
        """Revoke all active refresh-token families belonging to a user."""
        collection = RefreshTokenSession.get_pymongo_collection()
        result = await collection.update_many(
            {"user_id": user_id, "revoked_at": None},
            {
                "$set": {
                    "revoked_at": now,
                    "revocation_reason": reason,
                    "updated_at": now,
                }
            },
        )
        return result.modified_count
