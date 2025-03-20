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
            user_id: User ID (string or ObjectId)

        Returns:
            Optional[Portfolio]: Active portfolio if found, None otherwise
        """
        # Try with the user_id as is
        portfolio = await Portfolio.find_one({"user_id": user_id, "is_active": True})
        
        # If not found and user_id is a string that could be an ObjectId, try converting
        if not portfolio and isinstance(user_id, str) and ObjectId.is_valid(user_id):
            portfolio = await Portfolio.find_one({"user_id": ObjectId(user_id), "is_active": True})
            
        return portfolio

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

    # Enhanced methods for direct section access
    
    async def get_portfolio_by_user_id(self, user_id: str) -> Optional[Portfolio]:
        """
        Get a portfolio by user ID, handling ObjectId conversion.
        
        This method tries both string and ObjectId versions of the user_id.
        
        Args:
            user_id: User ID (string or ObjectId)
            
        Returns:
            Optional[Portfolio]: Portfolio if found, None otherwise
        """
        # Get active portfolio first
        portfolio = await self.get_active_by_user_id(user_id)
        
        # If not found, try getting any portfolio
        if not portfolio:
            portfolios = await self.get_by_user_id(user_id)
            if portfolios:
                portfolio = portfolios[0]
                
        return portfolio
    
    async def get_career_summary(self, user_id: str) -> Optional[CareerSummary]:
        """
        Get career summary for a user.
        
        Args:
            user_id: User ID (string or ObjectId)
            
        Returns:
            Optional[CareerSummary]: Career summary if found, None otherwise
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)
        return portfolio.career_summary if portfolio else None
    
    async def get_skills(self, user_id: str) -> List[Skill]:
        """
        Get skills for a user.
        
        Args:
            user_id: User ID (string or ObjectId)
            
        Returns:
            List[Skill]: List of skills
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)
        return portfolio.skills if portfolio and portfolio.skills else []
    
    async def get_work_experience(self, user_id: str) -> List[WorkExperience]:
        """
        Get work experience for a user.
        
        Args:
            user_id: User ID (string or ObjectId)
            
        Returns:
            List[WorkExperience]: List of work experience entries
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)
        return portfolio.work_experience if portfolio and portfolio.work_experience else []
    
    async def get_education(self, user_id: str) -> List[Education]:
        """
        Get education for a user.
        
        Args:
            user_id: User ID (string or ObjectId)
            
        Returns:
            List[Education]: List of education entries
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)
        return portfolio.education if portfolio and portfolio.education else []
    
    async def get_projects(self, user_id: str) -> List[Project]:
        """
        Get projects for a user.
        
        Args:
            user_id: User ID (string or ObjectId)
            
        Returns:
            List[Project]: List of project entries
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)
        return portfolio.projects if portfolio and portfolio.projects else []
    
    async def get_awards(self, user_id: str) -> List[Award]:
        """
        Get awards for a user.
        
        Args:
            user_id: User ID (string or ObjectId)
            
        Returns:
            List[Award]: List of award entries
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)
        return portfolio.awards if portfolio and portfolio.awards else []
    
    async def get_publications(self, user_id: str) -> List[Publication]:
        """
        Get publications for a user.
        
        Args:
            user_id: User ID (string or ObjectId)
            
        Returns:
            List[Publication]: List of publication entries
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)
        return portfolio.publications if portfolio and portfolio.publications else []
    
    async def get_certifications(self, user_id: str) -> List[str]:
        """
        Get certifications for a user.
        
        Args:
            user_id: User ID (string or ObjectId)
            
        Returns:
            List[str]: List of certifications
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)
        return portfolio.certifications if portfolio and portfolio.certifications else []
    
    async def get_custom_sections(self, user_id: str) -> Optional[CustomSections]:
        """
        Get custom sections config for a user.
        
        Args:
            user_id: User ID (string or ObjectId)
            
        Returns:
            Optional[CustomSections]: Custom sections config if found, None otherwise
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)
        return portfolio.custom_sections if portfolio else None
