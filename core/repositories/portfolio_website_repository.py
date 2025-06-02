"""Portfolio website repository for database operations."""

from typing import List, Optional

from beanie import PydanticObjectId
from pymongo.errors import DuplicateKeyError

from config.logging_config import get_logger

from ..exceptions.base import ConflictException
from ..models.portfolio_website import PortfolioWebsite


class PortfolioWebsiteRepository:
    """Repository for portfolio website operations."""

    def __init__(self):
        """Initialize repository."""
        self.logger = get_logger(self.__class__.__name__)

    async def create(self, website: PortfolioWebsite) -> PortfolioWebsite:
        """
        Create a new portfolio website.

        Args:
            website: Portfolio website to create

        Returns:
            PortfolioWebsite: Created website

        Raises:
            ConflictException: If subdomain already exists
        """
        try:
            await website.insert()
            self.logger.info(
                f"Created portfolio website with subdomain: {website.subdomain}"
            )
            return website
        except DuplicateKeyError as e:
            self.logger.warning(f"Subdomain already exists: {website.subdomain}")
            raise ConflictException(f"Subdomain '{website.subdomain}' is already taken")

    async def get_by_id(
        self, website_id: PydanticObjectId
    ) -> Optional[PortfolioWebsite]:
        """
        Get portfolio website by ID.

        Args:
            website_id: Website ID

        Returns:
            Optional[PortfolioWebsite]: Website if found
        """
        website = await PortfolioWebsite.get(website_id)
        if website:
            self.logger.debug(f"Found portfolio website: {website_id}")
        return website

    async def get_by_user_id(
        self, user_id: PydanticObjectId
    ) -> Optional[PortfolioWebsite]:
        """
        Get portfolio website by user ID.

        Args:
            user_id: User ID

        Returns:
            Optional[PortfolioWebsite]: Website if found
        """
        website = await PortfolioWebsite.find_one(PortfolioWebsite.user_id == user_id)
        if website:
            self.logger.debug(f"Found portfolio website for user: {user_id}")
        return website

    async def get_by_subdomain(self, subdomain: str) -> Optional[PortfolioWebsite]:
        """
        Get portfolio website by subdomain.

        Args:
            subdomain: Subdomain to search for

        Returns:
            Optional[PortfolioWebsite]: Website if found
        """
        website = await PortfolioWebsite.find_one(
            PortfolioWebsite.subdomain == subdomain
        )
        if website:
            self.logger.debug(f"Found portfolio website for subdomain: {subdomain}")
        return website

    async def get_by_portfolio_id(
        self, portfolio_id: PydanticObjectId
    ) -> Optional[PortfolioWebsite]:
        """
        Get portfolio website by portfolio ID.

        Args:
            portfolio_id: Portfolio ID

        Returns:
            Optional[PortfolioWebsite]: Website if found
        """
        website = await PortfolioWebsite.find_one(
            PortfolioWebsite.portfolio_id == portfolio_id
        )
        if website:
            self.logger.debug(f"Found portfolio website for portfolio: {portfolio_id}")
        return website

    async def update(
        self, website_id: PydanticObjectId, website: PortfolioWebsite
    ) -> Optional[PortfolioWebsite]:
        """
        Update portfolio website.

        Args:
            website_id: Website ID to update
            website: Updated website data

        Returns:
            Optional[PortfolioWebsite]: Updated website if successful
        """
        existing_website = await self.get_by_id(website_id)
        if not existing_website:
            return None

        await existing_website.set(website.model_dump(exclude={"id"}))
        self.logger.info(f"Updated portfolio website: {website_id}")
        return existing_website

    async def delete(self, website_id: PydanticObjectId) -> bool:
        """
        Delete portfolio website.

        Args:
            website_id: Website ID to delete

        Returns:
            bool: True if deleted successfully
        """
        website = await self.get_by_id(website_id)
        if not website:
            return False

        await website.delete()
        self.logger.info(f"Deleted portfolio website: {website_id}")
        return True

    async def list_by_user_id(
        self, user_id: PydanticObjectId
    ) -> List[PortfolioWebsite]:
        """
        List all portfolio websites for a user.

        Args:
            user_id: User ID

        Returns:
            List[PortfolioWebsite]: List of websites
        """
        websites = await PortfolioWebsite.find(
            PortfolioWebsite.user_id == user_id
        ).to_list()
        self.logger.debug(
            f"Found {len(websites)} portfolio websites for user: {user_id}"
        )
        return websites

    async def list_published_websites(
        self, limit: int = 100, skip: int = 0
    ) -> List[PortfolioWebsite]:
        """
        List published portfolio websites.

        Args:
            limit: Maximum number of websites to return
            skip: Number of websites to skip

        Returns:
            List[PortfolioWebsite]: List of published websites
        """
        websites = (
            await PortfolioWebsite.find(PortfolioWebsite.is_published == True)
            .skip(skip)
            .limit(limit)
            .to_list()
        )

        self.logger.debug(f"Found {len(websites)} published portfolio websites")
        return websites

    async def check_subdomain_availability(self, subdomain: str) -> bool:
        """
        Check if a subdomain is available.

        Args:
            subdomain: Subdomain to check

        Returns:
            bool: True if available, False if taken
        """
        existing = await self.get_by_subdomain(subdomain)
        available = existing is None
        self.logger.debug(f"Subdomain '{subdomain}' availability: {available}")
        return available

    async def suggest_alternative_subdomains(
        self, base_subdomain: str, count: int = 5
    ) -> List[str]:
        """
        Suggest alternative subdomains if the requested one is taken.

        Args:
            base_subdomain: Base subdomain to generate alternatives from
            count: Number of suggestions to generate

        Returns:
            List[str]: List of available alternative subdomains
        """
        suggestions = []

        # Try with numbers
        for i in range(1, count + 5):
            candidate = f"{base_subdomain}{i}"
            if await self.check_subdomain_availability(candidate):
                suggestions.append(candidate)
                if len(suggestions) >= count:
                    break

        # Try with common variations if not enough found
        if len(suggestions) < count:
            variations = [
                f"{base_subdomain}dev",
                f"{base_subdomain}pro",
                f"{base_subdomain}portfolio",
                f"the{base_subdomain}",
                f"{base_subdomain}official",
            ]

            for variation in variations:
                if len(suggestions) >= count:
                    break
                if await self.check_subdomain_availability(variation):
                    suggestions.append(variation)

        self.logger.debug(
            f"Generated {len(suggestions)} alternative subdomains for '{base_subdomain}'"
        )
        return suggestions[:count]

    async def update_deployment_status(
        self, website_id: PydanticObjectId, status: str, **kwargs
    ) -> Optional[PortfolioWebsite]:
        """
        Update deployment status of a portfolio website.

        Args:
            website_id: Website ID
            status: New deployment status
            **kwargs: Additional deployment fields to update

        Returns:
            Optional[PortfolioWebsite]: Updated website if successful
        """
        website = await self.get_by_id(website_id)
        if not website:
            return None

        # Update deployment status
        website.deployment.status = status

        # Update other deployment fields if provided
        for key, value in kwargs.items():
            if hasattr(website.deployment, key):
                setattr(website.deployment, key, value)

        await website.save()
        self.logger.info(
            f"Updated deployment status for website {website_id}: {status}"
        )
        return website

    async def get_websites_by_status(self, status: str) -> List[PortfolioWebsite]:
        """
        Get websites by deployment status.

        Args:
            status: Deployment status to filter by

        Returns:
            List[PortfolioWebsite]: Websites with the specified status
        """
        websites = await PortfolioWebsite.find(
            PortfolioWebsite.deployment.status == status
        ).to_list()

        self.logger.debug(f"Found {len(websites)} websites with status: {status}")
        return websites
