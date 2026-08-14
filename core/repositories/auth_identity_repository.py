"""Repository for external and native authentication identities."""

from beanie import PydanticObjectId

from core.auth.types import IdentityProvider
from core.models.auth_identity import AuthIdentity

from .base_repository import BeanieRepository


class AuthIdentityRepository(BeanieRepository[AuthIdentity]):
    """Access provider identities by their stable provider subject."""

    def __init__(self) -> None:
        super().__init__(AuthIdentity)

    async def get_by_provider_subject(
        self,
        provider: IdentityProvider,
        provider_subject: str,
    ) -> AuthIdentity | None:
        """Find the unique identity asserted by a provider."""
        return await AuthIdentity.find_one(
            {
                "provider": provider,
                "provider_subject": provider_subject,
            }
        )

    async def list_by_user(self, user_id: PydanticObjectId) -> list[AuthIdentity]:
        """List all identities linked to a user."""
        return await AuthIdentity.find({"user_id": user_id}).to_list()
