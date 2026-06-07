"""Repository for portfolio site tokens."""

from datetime import UTC, datetime

from beanie import PydanticObjectId

from core.models.portfolio_site_token import PortfolioSiteToken
from core.utils.portfolio_site_token import hash_token

from .base_repository import BeanieRepository


class PortfolioSiteTokenRepository(BeanieRepository[PortfolioSiteToken]):
    """Repository for PortfolioSiteToken documents."""

    def __init__(self) -> None:
        super().__init__(PortfolioSiteToken)

    async def get_active_by_raw_token(
        self, raw_token: str
    ) -> PortfolioSiteToken | None:
        """Find an active token record by raw token value."""
        token_hash = hash_token(raw_token)
        return await PortfolioSiteToken.find_one(
            {"token_hash": token_hash, "is_active": True}
        )

    async def touch_last_used(self, token_id: PydanticObjectId) -> None:
        """Update last_used_at for audit."""
        token = await PortfolioSiteToken.get(token_id)
        if token:
            token.last_used_at = datetime.now(UTC)
            token.updated_at = datetime.now(UTC)
            await token.save()
