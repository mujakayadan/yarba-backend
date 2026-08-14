"""Repository for atomic OAuth nonce consumption."""

from datetime import datetime
from typing import Any, cast

from pymongo import ReturnDocument

from core.auth.types import IdentityProvider
from core.models.oauth_nonce import OAuthNonce

from .base_repository import BeanieRepository


class OAuthNonceRepository(BeanieRepository[OAuthNonce]):
    """Persist and atomically consume short-lived OAuth nonce state."""

    def __init__(self) -> None:
        super().__init__(OAuthNonce)

    async def consume(
        self,
        *,
        cookie_hash: str,
        provider: IdentityProvider,
        now: datetime,
    ) -> OAuthNonce | None:
        """Consume an unexpired matching nonce once."""
        document: (
            dict[str, Any] | None
        ) = await OAuthNonce.get_pymongo_collection().find_one_and_update(
            {
                "cookie_hash": cookie_hash,
                "provider": provider,
                "expires_at": {"$gt": now},
                "consumed_at": None,
            },
            {"$set": {"consumed_at": now}},
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            return None
        return cast(OAuthNonce, OAuthNonce.model_validate(document))
