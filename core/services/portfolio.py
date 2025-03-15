"""Portfolio service for user portfolio management."""

import logging
from typing import Dict, List, Optional

from ..exceptions.base import NotFoundException
from ..models.portfolio import Portfolio, PortfolioItem
from ..models.user import User
from ..repositories.portfolio import PortfolioRepository
from ..repositories.user import UserRepository

logger = logging.getLogger(__name__)


class PortfolioService:
    """Service for handling user portfolio related operations."""

    def __init__(
        self,
        portfolio_repository: PortfolioRepository,
        user_repository: UserRepository,
    ):
        """
        Initialize the service.

        Args:
            portfolio_repository: Portfolio repository instance
            user_repository: User repository instance
        """
        self.portfolio_repository = portfolio_repository
        self.user_repository = user_repository
        self.logger = logging.getLogger(self.__class__.__name__)

    async def get_portfolio(self, user_id: str) -> Portfolio:
        """
        Get a user's portfolio.

        Args:
            user_id: User ID

        Returns:
            Portfolio: User portfolio

        Raises:
            NotFoundException: If portfolio not found
        """
        portfolio = await self.portfolio_repository.get_by_user_id(user_id)

        if not portfolio:
            self.logger.warning(f"Portfolio not found for user: {user_id}")
            raise NotFoundException("Portfolio not found")

        return portfolio

    async def create_portfolio(
        self, user_id: str, title: str = "My Portfolio"
    ) -> Portfolio:
        """
        Create a new portfolio for a user.

        Args:
            user_id: User ID
            title: Portfolio title

        Returns:
            Portfolio: Created portfolio

        Raises:
            NotFoundException: If user not found
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            self.logger.warning(f"User not found: {user_id}")
            raise NotFoundException("User not found")

        # Check if portfolio already exists
        existing_portfolio = await self.portfolio_repository.get_by_user_id(user_id)
        if existing_portfolio:
            self.logger.info(f"Portfolio already exists for user: {user_id}")
            return existing_portfolio

        portfolio = await self.portfolio_repository.create_for_user(user, title)
        self.logger.info(f"Portfolio created for user: {user_id}")

        return portfolio

    async def update_portfolio(self, user_id: str, update_data: Dict) -> Portfolio:
        """
        Update a user's portfolio.

        Args:
            user_id: User ID
            update_data: Portfolio data to update

        Returns:
            Portfolio: Updated portfolio

        Raises:
            NotFoundException: If portfolio not found
        """
        portfolio = await self.get_portfolio(user_id)

        # Update portfolio fields
        for key, value in update_data.items():
            if (
                hasattr(portfolio, key)
                and key != "id"
                and key != "user"
                and key != "items"
            ):
                setattr(portfolio, key, value)

        updated_portfolio = await self.portfolio_repository.update(
            portfolio.id, portfolio
        )
        if not updated_portfolio:
            self.logger.error(f"Failed to update portfolio for user: {user_id}")
            raise NotFoundException("Portfolio not found")

        self.logger.info(f"Portfolio updated for user: {user_id}")
        return updated_portfolio

    async def add_portfolio_item(self, user_id: str, item: PortfolioItem) -> Portfolio:
        """
        Add an item to a user's portfolio.

        Args:
            user_id: User ID
            item: Portfolio item to add

        Returns:
            Portfolio: Updated portfolio

        Raises:
            NotFoundException: If portfolio not found
        """
        portfolio = await self.get_portfolio(user_id)

        result = await self.portfolio_repository.add_item(portfolio.id, item)
        if not result:
            self.logger.error(f"Failed to add portfolio item for user: {user_id}")
            raise NotFoundException("Portfolio not found")

        # Get updated portfolio
        updated_portfolio = await self.get_portfolio(user_id)

        self.logger.info(f"Portfolio item added for user: {user_id}")
        return updated_portfolio

    async def update_portfolio_item(
        self, user_id: str, item_title: str, updated_item: PortfolioItem
    ) -> Portfolio:
        """
        Update an item in a user's portfolio.

        Args:
            user_id: User ID
            item_title: Title of the item to update
            updated_item: Updated portfolio item

        Returns:
            Portfolio: Updated portfolio

        Raises:
            NotFoundException: If portfolio not found
        """
        portfolio = await self.get_portfolio(user_id)

        result = await self.portfolio_repository.update_item(
            portfolio.id, item_title, updated_item
        )
        if not result:
            self.logger.warning(f"Failed to update portfolio item for user: {user_id}")
            # Item might not exist, so we don't raise an exception

        # Get updated portfolio
        updated_portfolio = await self.get_portfolio(user_id)

        self.logger.info(f"Portfolio item updated for user: {user_id}")
        return updated_portfolio

    async def remove_portfolio_item(self, user_id: str, item_title: str) -> Portfolio:
        """
        Remove an item from a user's portfolio.

        Args:
            user_id: User ID
            item_title: Title of the item to remove

        Returns:
            Portfolio: Updated portfolio

        Raises:
            NotFoundException: If portfolio not found
        """
        portfolio = await self.get_portfolio(user_id)

        result = await self.portfolio_repository.remove_item(portfolio.id, item_title)
        if not result:
            self.logger.warning(f"Failed to remove portfolio item for user: {user_id}")
            # Item might not exist, so we don't raise an exception

        # Get updated portfolio
        updated_portfolio = await self.get_portfolio(user_id)

        self.logger.info(f"Portfolio item removed for user: {user_id}")
        return updated_portfolio

    async def get_public_portfolios(self) -> List[Portfolio]:
        """
        Get all public portfolios.

        Returns:
            List[Portfolio]: List of public portfolios
        """
        return await self.portfolio_repository.get_public_portfolios()

    async def update_portfolio_visibility(
        self, user_id: str, is_public: bool
    ) -> Portfolio:
        """
        Update a user's portfolio visibility.

        Args:
            user_id: User ID
            is_public: Whether the portfolio is public

        Returns:
            Portfolio: Updated portfolio

        Raises:
            NotFoundException: If portfolio not found
        """
        portfolio = await self.get_portfolio(user_id)

        result = await self.portfolio_repository.update_visibility(
            portfolio.id, is_public
        )
        if not result:
            self.logger.error(
                f"Failed to update portfolio visibility for user: {user_id}"
            )
            raise NotFoundException("Portfolio not found")

        # Get updated portfolio
        updated_portfolio = await self.get_portfolio(user_id)

        self.logger.info(f"Portfolio visibility updated for user: {user_id}")
        return updated_portfolio
