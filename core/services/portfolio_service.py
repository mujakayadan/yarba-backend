"""Portfolio service for user portfolio management."""

from typing import Dict, List

from beanie import PydanticObjectId

from config.logging_config import get_logger

from ..exceptions.base import NotFoundException
from ..models.portfolio import (
    Award,
    CareerSummary,
    Education,
    Portfolio,
    Project,
    Publication,
    Skill,
    WorkExperience,
)
from ..repositories.portfolio_repository import PortfolioRepository
from ..repositories.user_repository import UserRepository

logger = get_logger(__name__)


class PortfolioService:
    """Service for portfolio operations."""

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
        self.logger = get_logger(self.__class__.__name__)

    async def get_portfolio_by_user_id(self, user_id: PydanticObjectId) -> Portfolio:
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

    async def get_portfolio_by_id(self, portfolio_id: PydanticObjectId) -> Portfolio:
        """
        Get a portfolio by its ID.

        Args:
            portfolio_id: Portfolio ID

        Returns:
            Portfolio: Found portfolio

        Raises:
            NotFoundException: If portfolio not found
        """
        self.logger.debug(f"Getting portfolio by ID: {portfolio_id}")

        try:
            portfolio = await self.portfolio_repository.get_by_id(portfolio_id)

            if not portfolio:
                self.logger.warning(f"Portfolio not found with ID: {portfolio_id}")
                raise NotFoundException(f"Portfolio not found with ID: {portfolio_id}")

            self.logger.debug(f"Found portfolio with ID: {portfolio_id}")
            return portfolio

        except Exception as e:
            self.logger.error(f"Error retrieving portfolio with ID {portfolio_id}: {e}")
            raise NotFoundException(f"Could not retrieve portfolio: {str(e)}")

    async def create_portfolio(self, user_id: PydanticObjectId) -> Portfolio:
        """
        Create a new portfolio for a user or return existing one.

        Args:
            user_id: User ID

        Returns:
            Portfolio: Created or existing portfolio

        Raises:
            NotFoundException: If user not found
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            self.logger.warning(f"User not found: {user_id}")
            raise NotFoundException("User not found")

        # Check if portfolio already exists - will be handled by repository
        portfolio = await self.portfolio_repository.create_for_user(user.id)
        self.logger.info(f"Portfolio retrieved or created for user: {user_id}")

        return portfolio

    async def update_portfolio(
        self, user_id: PydanticObjectId, update_data: Dict
    ) -> Portfolio:
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
        portfolio = await self.get_portfolio_by_user_id(user_id)

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

    # Skills section management
    async def update_skills(
        self, user_id: PydanticObjectId, skills: List[Skill]
    ) -> Portfolio:
        """
        Update a user's skills.

        Args:
            user_id: User ID
            skills: Updated skills

        Returns:
            Portfolio: Updated portfolio

        Raises:
            NotFoundException: If portfolio not found
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)

        # Update skills in the portfolio
        result = await self.portfolio_repository.update_skills(portfolio.id, skills)
        if not result:
            self.logger.error(f"Failed to update skills for user: {user_id}")
            raise NotFoundException("Portfolio not found")

        # Get updated portfolio
        updated_portfolio = await self.get_portfolio_by_user_id(user_id)

        self.logger.info(f"Skills updated for user: {user_id}")
        return updated_portfolio

    async def add_skill_category(
        self, user_id: PydanticObjectId, category: Skill
    ) -> Portfolio:
        """
        Add a skill category to a user's portfolio.

        Args:
            user_id: User ID
            category: Skill category to add

        Returns:
            Portfolio: Updated portfolio

        Raises:
            NotFoundException: If portfolio not found
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)

        # Get current skills and add the new category if it doesn't exist
        current_skills = portfolio.skills if portfolio.skills else []

        # Check if category already exists
        for i, existing_category in enumerate(current_skills):
            if existing_category.category == category.category:
                # Update existing category
                current_skills[i] = category
                break
        else:
            # Category doesn't exist, add it
            current_skills.append(category)

        # Update skills in the portfolio
        result = await self.portfolio_repository.update_skills(
            portfolio.id, current_skills
        )
        if not result:
            self.logger.warning(f"Failed to add skill category for user: {user_id}")
            raise NotFoundException("Portfolio not found")

        # Get updated portfolio
        updated_portfolio = await self.get_portfolio_by_user_id(user_id)

        self.logger.info(f"Skill category added for user: {user_id}")
        return updated_portfolio

    async def remove_skill_category(
        self, user_id: PydanticObjectId, category_name: str
    ) -> Portfolio:
        """
        Remove a skill category from a user's portfolio.

        Args:
            user_id: User ID
            category_name: Name of the category to remove

        Returns:
            Portfolio: Updated portfolio

        Raises:
            NotFoundException: If portfolio not found
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)

        # Get current skills and remove the category if it exists
        current_skills = portfolio.skills if portfolio.skills else []
        updated_skills = [
            cat for cat in current_skills if cat.category != category_name
        ]

        # If skills didn't change, category might not exist
        if len(current_skills) == len(updated_skills):
            self.logger.warning(
                f"Skill category '{category_name}' not found for user: {user_id}"
            )
            return portfolio

        # Update skills in the portfolio
        result = await self.portfolio_repository.update_skills(
            portfolio.id, updated_skills
        )
        if not result:
            self.logger.warning(f"Failed to remove skill category for user: {user_id}")
            raise NotFoundException("Portfolio not found")

        # Get updated portfolio
        updated_portfolio = await self.get_portfolio_by_user_id(user_id)

        self.logger.info(f"Skill category removed for user: {user_id}")
        return updated_portfolio

    # Work Experience section management
    async def update_work_experience(
        self, user_id: PydanticObjectId, work_experience: List[WorkExperience]
    ) -> Portfolio:
        """
        Update a user's work experience.

        Args:
            user_id: User ID
            work_experience: Updated work experience entries

        Returns:
            Portfolio: Updated portfolio

        Raises:
            NotFoundException: If portfolio not found
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)

        # Update work experience in the portfolio
        result = await self.portfolio_repository.update_work_experience(
            portfolio.id, work_experience
        )
        if not result:
            self.logger.error(f"Failed to update work experience for user: {user_id}")
            raise NotFoundException("Portfolio not found")

        # Get updated portfolio
        updated_portfolio = await self.get_portfolio_by_user_id(user_id)

        self.logger.info(f"Work experience updated for user: {user_id}")
        return updated_portfolio

    async def add_work_experience(
        self, user_id: PydanticObjectId, experience: WorkExperience
    ) -> Portfolio:
        """
        Add a work experience entry to a user's portfolio.

        Args:
            user_id: User ID
            experience: Work experience entry to add

        Returns:
            Portfolio: Updated portfolio

        Raises:
            NotFoundException: If portfolio not found
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)

        # Get current work experience and add the new entry
        current_experiences = (
            portfolio.work_experience if portfolio.work_experience else []
        )
        current_experiences.append(experience)

        # Update work experience in the portfolio
        result = await self.portfolio_repository.update_work_experience(
            portfolio.id, current_experiences
        )
        if not result:
            self.logger.warning(f"Failed to add work experience for user: {user_id}")
            raise NotFoundException("Portfolio not found")

        # Get updated portfolio
        updated_portfolio = await self.get_portfolio_by_user_id(user_id)

        self.logger.info(f"Work experience added for user: {user_id}")
        return updated_portfolio

    # Education section management
    async def update_education(
        self, user_id: PydanticObjectId, education: List[Education]
    ) -> Portfolio:
        """
        Update a user's education information.

        Args:
            user_id: User ID
            education: Updated education entries

        Returns:
            Portfolio: Updated portfolio

        Raises:
            NotFoundException: If portfolio not found
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)

        # Update education in the portfolio
        result = await self.portfolio_repository.update_education(
            portfolio.id, education
        )
        if not result:
            self.logger.error(f"Failed to update education for user: {user_id}")
            raise NotFoundException("Portfolio not found")

        # Get updated portfolio
        updated_portfolio = await self.get_portfolio_by_user_id(user_id)

        self.logger.info(f"Education updated for user: {user_id}")
        return updated_portfolio

    async def add_education(
        self, user_id: PydanticObjectId, education_entry: Education
    ) -> Portfolio:
        """
        Add an education entry to a user's portfolio.

        Args:
            user_id: User ID
            education_entry: Education entry to add

        Returns:
            Portfolio: Updated portfolio

        Raises:
            NotFoundException: If portfolio not found
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)

        # Get current education entries and add the new entry
        current_education = portfolio.education if portfolio.education else []
        current_education.append(education_entry)

        # Update education in the portfolio
        result = await self.portfolio_repository.update_education(
            portfolio.id, current_education
        )
        if not result:
            self.logger.warning(f"Failed to add education entry for user: {user_id}")
            raise NotFoundException("Portfolio not found")

        # Get updated portfolio
        updated_portfolio = await self.get_portfolio_by_user_id(user_id)

        self.logger.info(f"Education entry added for user: {user_id}")
        return updated_portfolio

    # Projects section management
    async def update_projects(
        self, user_id: PydanticObjectId, projects: List[Project]
    ) -> Portfolio:
        """
        Update a user's projects.

        Args:
            user_id: User ID
            projects: Updated project entries

        Returns:
            Portfolio: Updated portfolio

        Raises:
            NotFoundException: If portfolio not found
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)

        # Update projects in the portfolio
        result = await self.portfolio_repository.update_projects(portfolio.id, projects)
        if not result:
            self.logger.error(f"Failed to update projects for user: {user_id}")
            raise NotFoundException("Portfolio not found")

        # Get updated portfolio
        updated_portfolio = await self.get_portfolio_by_user_id(user_id)

        self.logger.info(f"Projects updated for user: {user_id}")
        return updated_portfolio

    async def add_project(
        self, user_id: PydanticObjectId, project: Project
    ) -> Portfolio:
        """
        Add a project to a user's portfolio.

        Args:
            user_id: User ID
            project: Project to add

        Returns:
            Portfolio: Updated portfolio

        Raises:
            NotFoundException: If portfolio not found
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)

        # Get current projects and add the new project
        current_projects = portfolio.projects if portfolio.projects else []
        current_projects.append(project)

        # Update projects in the portfolio
        result = await self.portfolio_repository.update_projects(
            portfolio.id, current_projects
        )
        if not result:
            self.logger.warning(f"Failed to add project for user: {user_id}")
            raise NotFoundException("Portfolio not found")

        # Get updated portfolio
        updated_portfolio = await self.get_portfolio_by_user_id(user_id)

        self.logger.info(f"Project added for user: {user_id}")
        return updated_portfolio

    # Awards section management
    async def update_awards(
        self, user_id: PydanticObjectId, awards: List[Award]
    ) -> Portfolio:
        """
        Update a user's awards.

        Args:
            user_id: User ID
            awards: Updated award entries

        Returns:
            Portfolio: Updated portfolio

        Raises:
            NotFoundException: If portfolio not found
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)

        # Update awards in the portfolio
        result = await self.portfolio_repository.update_awards(portfolio.id, awards)
        if not result:
            self.logger.error(f"Failed to update awards for user: {user_id}")
            raise NotFoundException("Portfolio not found")

        # Get updated portfolio
        updated_portfolio = await self.get_portfolio_by_user_id(user_id)

        self.logger.info(f"Awards updated for user: {user_id}")
        return updated_portfolio

    async def add_award(self, user_id: PydanticObjectId, award: Award) -> Portfolio:
        """
        Add an award to a user's portfolio.

        Args:
            user_id: User ID
            award: Award to add

        Returns:
            Portfolio: Updated portfolio

        Raises:
            NotFoundException: If portfolio not found
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)

        # Get current awards and add the new award
        current_awards = portfolio.awards if portfolio.awards else []
        current_awards.append(award)

        # Update awards in the portfolio
        result = await self.portfolio_repository.update_awards(
            portfolio.id, current_awards
        )
        if not result:
            self.logger.warning(f"Failed to add award for user: {user_id}")
            raise NotFoundException("Portfolio not found")

        # Get updated portfolio
        updated_portfolio = await self.get_portfolio_by_user_id(user_id)

        self.logger.info(f"Award added for user: {user_id}")
        return updated_portfolio

    # Publications section management
    async def update_publications(
        self, user_id: PydanticObjectId, publications: List[Publication]
    ) -> Portfolio:
        """
        Update a user's publications.

        Args:
            user_id: User ID
            publications: Updated publication entries

        Returns:
            Portfolio: Updated portfolio

        Raises:
            NotFoundException: If portfolio not found
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)

        # Update publications in the portfolio
        result = await self.portfolio_repository.update_publications(
            portfolio.id, publications
        )
        if not result:
            self.logger.error(f"Failed to update publications for user: {user_id}")
            raise NotFoundException("Portfolio not found")

        # Get updated portfolio
        updated_portfolio = await self.get_portfolio_by_user_id(user_id)

        self.logger.info(f"Publications updated for user: {user_id}")
        return updated_portfolio

    async def add_publication(
        self, user_id: PydanticObjectId, publication: Publication
    ) -> Portfolio:
        """
        Add a publication to a user's portfolio.

        Args:
            user_id: User ID
            publication: Publication to add

        Returns:
            Portfolio: Updated portfolio

        Raises:
            NotFoundException: If portfolio not found
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)

        # Get current publications and add the new publication
        current_publications = portfolio.publications if portfolio.publications else []
        current_publications.append(publication)

        # Update publications in the portfolio
        result = await self.portfolio_repository.update_publications(
            portfolio.id, current_publications
        )
        if not result:
            self.logger.warning(f"Failed to add publication for user: {user_id}")
            raise NotFoundException("Portfolio not found")

        # Get updated portfolio
        updated_portfolio = await self.get_portfolio_by_user_id(user_id)

        self.logger.info(f"Publication added for user: {user_id}")
        return updated_portfolio

    # Career Summary management
    async def update_career_summary(
        self, user_id: PydanticObjectId, career_summary: CareerSummary
    ) -> Portfolio:
        """
        Update a user's career summary.

        Args:
            user_id: User ID
            career_summary: Updated career summary

        Returns:
            Portfolio: Updated portfolio

        Raises:
            NotFoundException: If portfolio not found
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)

        # Update career summary in the portfolio
        result = await self.portfolio_repository.update_career_summary(
            portfolio.id, career_summary
        )
        if not result:
            self.logger.error(f"Failed to update career summary for user: {user_id}")
            raise NotFoundException("Portfolio not found")

        # Get updated portfolio
        updated_portfolio = await self.get_portfolio_by_user_id(user_id)

        self.logger.info(f"Career summary updated for user: {user_id}")
        return updated_portfolio
