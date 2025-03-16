"""Portfolio repository implementation."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from bson.objectid import ObjectId

from core.models.profile import Profile

from ..models.portfolio import (
    Award,
    CareerSummary,
    CustomSections,
    Education,
    Portfolio,
    Project,
    Publication,
    Skill,
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
        Get all portfolios for a user.

        Args:
            user: User

        Returns:
            List[Portfolio]: List of portfolios
        """
        return await Portfolio.find({"user_id": user.id}).to_list()

    async def get_by_user_id(self, user_id: str) -> List[Portfolio]:
        """
        Get all portfolios for a user by user ID.

        Args:
            user_id: User ID

        Returns:
            List[Portfolio]: List of portfolios
        """
        return await Portfolio.find({"user_id": user_id}).to_list()

    async def get_by_profile(self, profile: Profile) -> List[Portfolio]:
        """
        Get all portfolios for a profile.

        Args:
            profile: Profile

        Returns:
            List[Portfolio]: List of portfolios
        """
        return await Portfolio.find({"profile_id": profile.id}).to_list()

    async def get_by_profile_id(self, profile_id: str) -> List[Portfolio]:
        """
        Get all portfolios for a profile by profile ID.

        Args:
            profile_id: Profile ID

        Returns:
            List[Portfolio]: List of portfolios
        """
        return await Portfolio.find({"profile_id": profile_id}).to_list()

    async def get_active_by_user(self, user: User) -> Optional[Portfolio]:
        """
        Get the active portfolio for a user.

        Args:
            user: User

        Returns:
            Optional[Portfolio]: Active portfolio if found, None otherwise
        """
        return await Portfolio.find_one({"user_id": user.id, "is_active": True})

    async def get_active_by_user_id(self, user_id: str) -> Optional[Portfolio]:
        """
        Get the active portfolio for a user by user ID.

        Args:
            user_id: User ID

        Returns:
            Optional[Portfolio]: Active portfolio if found, None otherwise
        """
        return await Portfolio.find_one({"user_id": user_id, "is_active": True})

    async def get_active_portfolios(self) -> List[Portfolio]:
        """
        Get all active portfolios.

        Returns:
            List[Portfolio]: List of active portfolios
        """
        return await Portfolio.find({"is_active": True}).to_list()

    async def update_skills(self, portfolio_id: str, skills: List[Skill]) -> bool:
        """
        Update skills for a portfolio.

        Args:
            portfolio_id: Portfolio ID
            skills: List of Skill objects

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

    async def create_for_user(
        self, user_id: str, profile_id: Optional[str] = None
    ) -> Portfolio:
        """
        Create a new portfolio for a user.

        Args:
            user_id: The ID of the user to create the portfolio for
            profile_id: Optional profile ID to associate with the portfolio

        Returns:
            The created portfolio
        """
        now = datetime.utcnow()
        portfolio = Portfolio(
            user_id=ObjectId(user_id),
            profile_id=ObjectId(profile_id) if profile_id else None,
            professional_title="",
            career_summary=CareerSummary(
                job_titles=[],
                years_of_experience="",
                default_summary="",
            ),
            skills=[],
            work_experience=[],
            education=[],
            projects=[],
            awards=[],
            publications=[],
            certifications=[],
            custom_sections=CustomSections(enabled=[], order=[]),
            is_active=True,
            version="1.0",
            created_at=now,
            updated_at=now,
        )
        await portfolio.insert()
        return portfolio

    async def get_user(self, portfolio_id: str) -> Optional[User]:
        """Get the user associated with this portfolio."""
        portfolio = await Portfolio.find_one({"_id": portfolio_id})
        if not portfolio:
            return None
        return await User.get(portfolio.user_id)

    async def get_profile(self, portfolio_id: str) -> Optional[Profile]:
        """Get the profile associated with this portfolio."""
        portfolio = await Portfolio.find_one({"_id": portfolio_id})
        if not portfolio or not portfolio.profile_id:
            return None
        return await Profile.get(portfolio.profile_id)
