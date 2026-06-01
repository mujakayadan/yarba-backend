"""Portfolio repository implementation."""

from datetime import UTC, datetime

from beanie import PydanticObjectId

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
from .base_repository import BeanieRepository


class PortfolioRepository(BeanieRepository[Portfolio]):
    """Repository for Portfolio documents."""

    def __init__(self):
        """Initialize the repository."""
        super().__init__(Portfolio)

    async def get_by_user(self, user: User) -> Portfolio | None:
        """Get the portfolio for a user.

        Args:
            user: User

        Returns:
            Optional[Portfolio]: The user's portfolio if found, None otherwise
        """
        return await Portfolio.find_one({"user_id": user.id})

    async def get_by_user_id(self, user_id: PydanticObjectId) -> Portfolio | None:
        """Get the portfolio for a user by user ID.

        Args:
            user_id: User ID

        Returns:
            Optional[Portfolio]: The user's portfolio if found, None otherwise
        """
        return await Portfolio.find_one({"user_id": user_id})

    async def get_by_profile(self, profile: Profile) -> Portfolio | None:
        """Get the portfolio for a profile.

        Args:
            profile: Profile

        Returns:
            Optional[Portfolio]: The profile's portfolio if found, None otherwise
        """
        return await Portfolio.find_one({"profile_id": profile.id})

    async def get_by_profile_id(self, profile_id: PydanticObjectId) -> Portfolio | None:
        """Get the portfolio for a profile by profile ID.

        Args:
            profile_id: Profile ID

        Returns:
            Optional[Portfolio]: The profile's portfolio if found, None otherwise
        """
        return await Portfolio.find_one({"profile_id": profile_id})

    async def exists(self, portfolio_id: PydanticObjectId) -> bool:
        """Check if a portfolio with the given ID exists.

        Args:
            portfolio_id: Portfolio ID to check

        Returns:
            bool: True if portfolio exists, False otherwise
        """
        portfolio = await Portfolio.find_one({"_id": portfolio_id})
        return portfolio is not None

    async def update_skills(
        self, portfolio_id: PydanticObjectId, skills: list[Skill]
    ) -> bool:
        """Update skills for a portfolio.

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
        result.updated_at = datetime.now(UTC)
        await result.save()
        return True

    async def update_work_experience(
        self, portfolio_id: PydanticObjectId, work_experience: list[WorkExperience]
    ) -> bool:
        """Update work experience for a portfolio.

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
        result.updated_at = datetime.now(UTC)
        await result.save()
        return True

    async def update_education(
        self, portfolio_id: PydanticObjectId, education: list[Education]
    ) -> bool:
        """Update education for a portfolio.

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
        result.updated_at = datetime.now(UTC)
        await result.save()
        return True

    async def update_projects(
        self, portfolio_id: PydanticObjectId, projects: list[Project]
    ) -> bool:
        """Update projects for a portfolio.

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
        result.updated_at = datetime.now(UTC)
        await result.save()
        return True

    async def update_awards(
        self, portfolio_id: PydanticObjectId, awards: list[Award]
    ) -> bool:
        """Update awards for a portfolio.

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
        result.updated_at = datetime.now(UTC)
        await result.save()
        return True

    async def update_publications(
        self, portfolio_id: PydanticObjectId, publications: list[Publication]
    ) -> bool:
        """Update publications for a portfolio.

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
        result.updated_at = datetime.now(UTC)
        await result.save()
        return True

    async def update_career_summary(
        self, portfolio_id: PydanticObjectId, career_summary: CareerSummary
    ) -> bool:
        """Update career summary for a portfolio.

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
        result.updated_at = datetime.now(UTC)
        await result.save()
        return True

    async def create_for_user(
        self, user_id: PydanticObjectId, profile_id: PydanticObjectId | None = None
    ) -> Portfolio:
        """Create a new portfolio for a user. If the user already has a portfolio, return that one.

        Args:
            user_id: User ID for which to create the portfolio
            profile_id: Profile ID to associate with the portfolio (optional)

        Returns:
            The created or existing portfolio
        """
        # Check if user already has a portfolio
        existing_portfolio = await self.get_by_user_id(user_id)
        if existing_portfolio:
            return existing_portfolio

        # Create a new portfolio if one doesn't exist
        now = datetime.now(UTC)
        portfolio = Portfolio(
            user_id=user_id,
            profile_id=profile_id,
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
            created_at=now,
            updated_at=now,
        )
        await portfolio.insert()
        return portfolio

    async def get_user(self, portfolio_id: PydanticObjectId) -> User | None:
        """Get the user associated with this portfolio."""
        portfolio = await Portfolio.find_one({"_id": portfolio_id})
        if not portfolio:
            return None
        return await User.get(portfolio.user_id)

    async def get_profile(self, portfolio_id: PydanticObjectId) -> Profile | None:
        """Get the profile associated with this portfolio."""
        portfolio = await Portfolio.find_one({"_id": portfolio_id})
        if not portfolio or not portfolio.profile_id:
            return None
        return await Profile.get(portfolio.profile_id)

    # Enhanced methods for direct section access

    async def get_portfolio_by_user_id(
        self, user_id: PydanticObjectId
    ) -> Portfolio | None:
        """Get a portfolio by user ID.

        Args:
            user_id: User ID

        Returns:
            Optional[Portfolio]: Portfolio if found, None otherwise
        """
        return await self.get_by_user_id(user_id)

    async def get_career_summary(
        self, user_id: PydanticObjectId
    ) -> CareerSummary | None:
        """Get career summary for a user.

        Args:
            user_id: User ID

        Returns:
            Optional[CareerSummary]: Career summary if found, None otherwise
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)
        return portfolio.career_summary if portfolio else None

    async def get_skills(self, user_id: PydanticObjectId) -> list[Skill]:
        """Get skills for a user.

        Args:
            user_id: User ID

        Returns:
            List[Skill]: List of skills
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)
        return portfolio.skills if portfolio and portfolio.skills else []

    async def get_work_experience(
        self, user_id: PydanticObjectId
    ) -> list[WorkExperience]:
        """Get work experience for a user.

        Args:
            user_id: User ID

        Returns:
            List[WorkExperience]: List of work experience entries
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)
        return (
            portfolio.work_experience if portfolio and portfolio.work_experience else []
        )

    async def get_education(self, user_id: PydanticObjectId) -> list[Education]:
        """Get education for a user.

        Args:
            user_id: User ID

        Returns:
            List[Education]: List of education entries
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)
        return portfolio.education if portfolio and portfolio.education else []

    async def get_projects(self, user_id: PydanticObjectId) -> list[Project]:
        """Get projects for a user.

        Args:
            user_id: User ID

        Returns:
            List[Project]: List of project entries
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)
        return portfolio.projects if portfolio and portfolio.projects else []

    async def get_awards(self, user_id: PydanticObjectId) -> list[Award]:
        """Get awards for a user.

        Args:
            user_id: User ID

        Returns:
            List[Award]: List of award entries
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)
        return portfolio.awards if portfolio and portfolio.awards else []

    async def get_publications(self, user_id: PydanticObjectId) -> list[Publication]:
        """Get publications for a user.

        Args:
            user_id: User ID

        Returns:
            List[Publication]: List of publication entries
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)
        return portfolio.publications if portfolio and portfolio.publications else []

    async def get_certifications(self, user_id: PydanticObjectId) -> list[str]:
        """Get certifications for a user.

        Args:
            user_id: User ID

        Returns:
            List[str]: List of certifications
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)
        return (
            portfolio.certifications if portfolio and portfolio.certifications else []
        )

    async def get_custom_sections(
        self, user_id: PydanticObjectId
    ) -> CustomSections | None:
        """Get custom sections config for a user.

        Args:
            user_id: User ID

        Returns:
            Optional[CustomSections]: Custom sections config if found, None otherwise
        """
        portfolio = await self.get_portfolio_by_user_id(user_id)
        return portfolio.custom_sections if portfolio else None


async def get_portfolio_repository() -> PortfolioRepository:
    """Get the portfolio repository."""
    return PortfolioRepository()
