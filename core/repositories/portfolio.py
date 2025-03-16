"""Portfolio repository implementation."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models.portfolio import (
    Award,
    CareerSummary,
    Education,
    Portfolio,
    PortfolioItem,
    Project,
    Publication,
    SkillCategory,
    WorkExperience,
)
from ..models.user import User
from .base import BeanieRepository


class PortfolioRepository(BeanieRepository[Portfolio]):
    """Repository for Portfolio documents."""

    def __init__(self):
        """Initialize the repository."""
        super().__init__(Portfolio)

    async def get_by_user(self, user: User) -> List[Portfolio]:
        """
        Get portfolios for a user.

        Args:
            user: User

        Returns:
            List[Portfolio]: List of portfolios for the user
        """
        return await Portfolio.find({"user_id": user.id}).to_list()

    async def get_by_user_id(self, user_id: str) -> List[Portfolio]:
        """
        Get portfolios for a user by user ID.

        Args:
            user_id: User ID

        Returns:
            List[Portfolio]: List of portfolios for the user
        """
        return await Portfolio.find({"user_id": user_id}).to_list()

    async def get_active_portfolios(self) -> List[Portfolio]:
        """
        Get all active portfolios.

        Returns:
            List[Portfolio]: List of active portfolios
        """
        return await Portfolio.find({"is_active": True}).to_list()

    async def update_skills(
        self, portfolio_id: str, skills: List[Dict[str, List[str]]]
    ) -> bool:
        """
        Update skills for a portfolio.

        Args:
            portfolio_id: Portfolio ID
            skills: List of skill categories and their skills

        Returns:
            bool: True if successful, False otherwise
        """
        result = await Portfolio.find_one({"_id": portfolio_id})
        if not result:
            return False

        result.skills = skills
        result.updated_at = datetime.utcnow()
        await result.save()
        return True

    async def update_work_experience(
        self, portfolio_id: str, work_experience: List[WorkExperience]
    ) -> bool:
        """
        Update work experience for a portfolio.

        Args:
            portfolio_id: Portfolio ID
            work_experience: List of work experience entries

        Returns:
            bool: True if successful, False otherwise
        """
        result = await Portfolio.find_one({"_id": portfolio_id})
        if not result:
            return False

        result.work_experience = work_experience
        result.updated_at = datetime.utcnow()
        await result.save()
        return True

    async def update_education(
        self, portfolio_id: str, education: List[Education]
    ) -> bool:
        """
        Update education for a portfolio.

        Args:
            portfolio_id: Portfolio ID
            education: List of education entries

        Returns:
            bool: True if successful, False otherwise
        """
        result = await Portfolio.find_one({"_id": portfolio_id})
        if not result:
            return False

        result.education = education
        result.updated_at = datetime.utcnow()
        await result.save()
        return True

    async def update_projects(self, portfolio_id: str, projects: List[Project]) -> bool:
        """
        Update projects for a portfolio.

        Args:
            portfolio_id: Portfolio ID
            projects: List of project entries

        Returns:
            bool: True if successful, False otherwise
        """
        result = await Portfolio.find_one({"_id": portfolio_id})
        if not result:
            return False

        result.projects = projects
        result.updated_at = datetime.utcnow()
        await result.save()
        return True

    async def update_awards(self, portfolio_id: str, awards: List[Award]) -> bool:
        """
        Update awards for a portfolio.

        Args:
            portfolio_id: Portfolio ID
            awards: List of award entries

        Returns:
            bool: True if successful, False otherwise
        """
        result = await Portfolio.find_one({"_id": portfolio_id})
        if not result:
            return False

        result.awards = awards
        result.updated_at = datetime.utcnow()
        await result.save()
        return True

    async def update_publications(
        self, portfolio_id: str, publications: List[Publication]
    ) -> bool:
        """
        Update publications for a portfolio.

        Args:
            portfolio_id: Portfolio ID
            publications: List of publication entries

        Returns:
            bool: True if successful, False otherwise
        """
        result = await Portfolio.find_one({"_id": portfolio_id})
        if not result:
            return False

        result.publications = publications
        result.updated_at = datetime.utcnow()
        await result.save()
        return True

    async def update_career_summary(
        self, portfolio_id: str, career_summary: CareerSummary
    ) -> bool:
        """
        Update career summary for a portfolio.

        Args:
            portfolio_id: Portfolio ID
            career_summary: Career summary object

        Returns:
            bool: True if successful, False otherwise
        """
        result = await Portfolio.find_one({"_id": portfolio_id})
        if not result:
            return False

        result.career_summary = career_summary
        result.updated_at = datetime.utcnow()
        await result.save()
        return True

    async def create_item(self, item: PortfolioItem) -> PortfolioItem:
        """
        Create a new portfolio item.

        Args:
            item: Portfolio item to create

        Returns:
            PortfolioItem: Created portfolio item
        """
        await item.create()
        return item

    async def get_items_by_portfolio_id(self, portfolio_id: str) -> List[PortfolioItem]:
        """
        Get all items for a portfolio.

        Args:
            portfolio_id: Portfolio ID

        Returns:
            List[PortfolioItem]: List of portfolio items
        """
        return await PortfolioItem.find({"portfolio_id": portfolio_id}).to_list()

    async def update_item(self, item_id: str, updated_data: Dict[str, Any]) -> bool:
        """
        Update a portfolio item.

        Args:
            item_id: Item ID
            updated_data: Updated data

        Returns:
            bool: True if successful, False otherwise
        """
        result = await PortfolioItem.find_one({"_id": item_id})
        if not result:
            return False

        # Update fields
        for key, value in updated_data.items():
            if hasattr(result, key):
                setattr(result, key, value)

        result.updated_at = datetime.utcnow()
        await result.save()
        return True

    async def delete_item(self, item_id: str) -> bool:
        """
        Delete a portfolio item.

        Args:
            item_id: Item ID

        Returns:
            bool: True if successful, False otherwise
        """
        result = await PortfolioItem.find_one({"_id": item_id})
        if not result:
            return False

        await result.delete()
        return True

    async def update_active_status(self, portfolio_id: str, is_active: bool) -> bool:
        """
        Update active status for a portfolio.

        Args:
            portfolio_id: Portfolio ID
            is_active: Whether the portfolio is active

        Returns:
            bool: True if successful, False otherwise
        """
        result = await Portfolio.find_one({"_id": portfolio_id})
        if not result:
            return False

        result.is_active = is_active
        result.updated_at = datetime.utcnow()
        await result.save()
        return True

    async def create_for_user(
        self, user: User, title: str = "My Portfolio"
    ) -> Portfolio:
        """
        Create a new portfolio for a user.

        Args:
            user: User
            title: Portfolio title

        Returns:
            Portfolio: Created portfolio
        """
        portfolio = Portfolio(
            user_id=user.id,
            title=title,
            description="",
            professional_title=None,
            career_summary=CareerSummary(),
            skills=[],
            work_experience=[],
            education=[],
            projects=[],
            awards=[],
            publications=[],
            certifications=[],
            is_active=True,
            version="1.0",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        await portfolio.create()
        return portfolio
