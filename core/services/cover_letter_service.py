"""Cover letter service for cover letter management and generation."""

from typing import List, Optional

from beanie import PydanticObjectId

from config.logging_config import get_logger

from ..exceptions.base import NotFoundException
from ..models.cover_letter import CoverLetter
from ..repositories.cover_letter_repository import (
    CoverLetterFilter,
    CoverLetterRepository,
)
from ..repositories.portfolio_repository import PortfolioRepository
from ..repositories.profile_repository import ProfileRepository
from ..repositories.resume_repository import ResumeRepository
from ..repositories.user_repository import UserRepository
from ..services.job_service import JobService

logger = get_logger(__name__)


class CoverLetterService:
    """Service for cover letter operations."""

    def __init__(
        self,
        cover_letter_repository: CoverLetterRepository,
        user_repository: UserRepository,
        profile_repository: Optional[ProfileRepository] = None,
        portfolio_repository: Optional[PortfolioRepository] = None,
        resume_repository: Optional[ResumeRepository] = None,
        job_service: Optional[JobService] = None,
    ):
        """
        Initialize the service.

        Args:
            cover_letter_repository: Cover letter repository
            user_repository: User repository
            profile_repository: Profile repository (optional)
            portfolio_repository: Portfolio repository (optional)
            resume_repository: Resume repository (optional)
            job_service: Job service for extracting job information (optional)
        """
        self.cover_letter_repository = cover_letter_repository
        self.user_repository = user_repository
        self.profile_repository = profile_repository
        self.portfolio_repository = portfolio_repository
        self.resume_repository = resume_repository
        self.job_service = job_service
        self.logger = get_logger(self.__class__.__name__)

    async def get_cover_letter_by_id(
        self, cover_letter_id: PydanticObjectId, user_id: PydanticObjectId
    ) -> CoverLetter:
        """
        Get a cover letter by ID.

        Args:
            cover_letter_id: Cover letter ID
            user_id: User ID

        Returns:
            CoverLetter: Cover letter

        Raises:
            NotFoundException: If cover letter not found or doesn't belong to user
        """
        cover_letter = await self.cover_letter_repository.get_by_id(cover_letter_id)

        if not cover_letter:
            self.logger.warning(f"Cover letter not found: {cover_letter_id}")
            raise NotFoundException("Cover letter not found")

        # Check if the cover letter belongs to the user
        if cover_letter.user_id != user_id:
            self.logger.warning(
                f"Access denied: Cover letter {cover_letter_id} does not belong to user {user_id}"
            )
            raise NotFoundException("Cover letter not found")

        return cover_letter

    async def get_cover_letters_by_user(
        self, user_id: PydanticObjectId
    ) -> List[CoverLetter]:
        """
        Get all cover letters for a user.

        Args:
            user_id: User ID

        Returns:
            List[CoverLetter]: List of cover letters
        """
        return await self.cover_letter_repository.get_by_user_id(user_id)

    async def get_latest_cover_letter(
        self, user_id: PydanticObjectId
    ) -> Optional[CoverLetter]:
        """
        Get the most recent cover letter for a user.

        Args:
            user_id: User ID

        Returns:
            Optional[CoverLetter]: Most recent cover letter if found, None otherwise
        """
        return await self.cover_letter_repository.get_latest_by_user_id(user_id)

    async def create_cover_letter(
        self,
        user_id: PydanticObjectId,
        profile_id: Optional[PydanticObjectId] = None,
        portfolio_id: Optional[PydanticObjectId] = None,
        resume_id: Optional[PydanticObjectId] = None,
        title: Optional[str] = None,
        company_name: Optional[str] = None,
        job_title: Optional[str] = None,
        job_description: Optional[str] = None,
        template_id: Optional[str] = None,
    ) -> CoverLetter:
        """
        Create a new cover letter.

        Args:
            user_id: User ID
            profile_id: Profile ID (optional)
            portfolio_id: Portfolio ID (optional)
            resume_id: Resume ID (optional)
            title: Cover letter title (optional)
            company_name: Company name (optional)
            job_title: Job title (optional)
            job_description: Job description (optional)
            template_id: Template ID (optional)

        Returns:
            CoverLetter: Created cover letter

        Raises:
            NotFoundException: If user, profile, portfolio, or resume doesn't exist
        """
        # Verify user exists
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            self.logger.warning(f"User not found: {user_id}")
            raise NotFoundException("User not found")

        # Extract job info from description if not provided but job_description is available
        if job_description and self.job_service and (not company_name or not job_title):
            try:
                self.logger.info("Extracting job information from job description")
                job_info = await self.job_service.extract_job_info(job_description)

                if not company_name and job_info.get("company_name"):
                    company_name = job_info["company_name"]
                    self.logger.info(f"Extracted company name: {company_name}")

                if not job_title and job_info.get("job_title"):
                    job_title = job_info["job_title"]
                    self.logger.info(f"Extracted job title: {job_title}")
            except Exception as e:
                self.logger.error(f"Error extracting job info: {str(e)}")
                # Continue even if extraction fails

        # Verify profile exists if provided
        if profile_id and self.profile_repository:
            if not await self.profile_repository.exists(profile_id):
                self.logger.warning(f"Profile not found: {profile_id}")
                raise NotFoundException("Profile not found")

        # Verify portfolio exists if provided
        if portfolio_id and self.portfolio_repository:
            if not await self.portfolio_repository.exists(portfolio_id):
                self.logger.warning(f"Portfolio not found: {portfolio_id}")
                raise NotFoundException("Portfolio not found")

        # Verify resume exists if provided
        if resume_id and self.resume_repository:
            if not await self.resume_repository.exists(resume_id):
                self.logger.warning(f"Resume not found: {resume_id}")
                raise NotFoundException("Resume not found")

        # Create new cover letter
        cover_letter = CoverLetter(
            user_id=user_id,
            profile_id=profile_id,
            portfolio_id=portfolio_id,
            resume_id=resume_id,
            title=title or "My Cover Letter",
            company_name=company_name,
            job_title=job_title,
            job_description=job_description or "",
            template_id=template_id or "default",
        )

        # Save cover letter
        created_cover_letter = await self.cover_letter_repository.create(cover_letter)
        self.logger.info(f"Created new cover letter: {created_cover_letter.id}")

        return created_cover_letter

    async def update_cover_letter(
        self,
        cover_letter_id: PydanticObjectId,
        user_id: PydanticObjectId,
        **kwargs,
    ) -> CoverLetter:
        """
        Update a cover letter.

        Args:
            cover_letter_id: Cover letter ID
            user_id: User ID
            **kwargs: Fields to update

        Returns:
            CoverLetter: Updated cover letter

        Raises:
            NotFoundException: If cover letter not found or doesn't belong to user
        """
        # Verify cover letter exists and belongs to user
        cover_letter = await self.get_cover_letter_by_id(cover_letter_id, user_id)

        # Update fields
        updated_cover_letter = await self.cover_letter_repository.update_metadata(
            cover_letter_id=cover_letter_id, **kwargs
        )

        if not updated_cover_letter:
            self.logger.error(f"Failed to update cover letter {cover_letter_id}")
            raise NotFoundException("Cover letter not found")

        self.logger.info(f"Updated cover letter: {cover_letter_id}")
        return updated_cover_letter

    async def delete_cover_letter(
        self, cover_letter_id: PydanticObjectId, user_id: PydanticObjectId
    ) -> bool:
        """
        Delete a cover letter.

        Args:
            cover_letter_id: Cover letter ID
            user_id: User ID

        Returns:
            bool: True if deleted successfully

        Raises:
            NotFoundException: If cover letter not found or doesn't belong to user
        """
        # Verify cover letter exists and belongs to user
        cover_letter = await self.get_cover_letter_by_id(cover_letter_id, user_id)

        # Delete cover letter
        result = await self.cover_letter_repository.delete(cover_letter_id)
        self.logger.info(f"Deleted cover letter: {cover_letter_id}")
        return result

    async def filter_cover_letters(
        self, user_id: PydanticObjectId, filter_params: CoverLetterFilter
    ) -> List[CoverLetter]:
        """
        Filter cover letters by parameters.

        Args:
            user_id: User ID
            filter_params: Filter parameters

        Returns:
            List[CoverLetter]: List of filtered cover letters

        Raises:
            NotFoundException: If user not found
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            self.logger.warning(f"User not found: {user_id}")
            raise NotFoundException("User not found")

        return await self.cover_letter_repository.get_by_filter(user, filter_params)
