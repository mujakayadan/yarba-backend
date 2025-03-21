"""Resume service for resume management and generation."""

import logging
from typing import Dict, List, Optional

from config import settings

from ..exceptions.base import NotFoundException
from ..models.resume import Resume
from ..models.user import User
from ..repositories.resume import ResumeFilter, ResumeRepository
from ..repositories.user import UserRepository

logger = logging.getLogger(__name__)


class ResumeService:
    """Service for resume operations."""

    def __init__(
        self,
        resume_repository: ResumeRepository,
        user_repository: UserRepository,
    ):
        """
        Initialize the service.

        Args:
            resume_repository: Resume repository instance
            user_repository: User repository instance
        """
        self.resume_repository = resume_repository
        self.user_repository = user_repository
        self.logger = logging.getLogger(self.__class__.__name__)

    async def get_resume_by_id(self, resume_id: str, user_id: str) -> Resume:
        """
        Get a resume by ID.

        Args:
            resume_id: Resume ID
            user_id: User ID

        Returns:
            Resume: Resume

        Raises:
            NotFoundException: If resume not found or doesn't belong to user
        """
        resume = await self.resume_repository.get_by_id(resume_id)

        if not resume or str(resume.user.id) != user_id:
            self.logger.warning(
                f"Resume not found or access denied: {resume_id} for user {user_id}"
            )
            raise NotFoundException("Resume not found")

        return resume

    async def get_resumes_by_user(self, user_id: str) -> List[Resume]:
        """
        Get all resumes for a user.

        Args:
            user_id: User ID

        Returns:
            List[Resume]: List of resumes
        """
        return await self.resume_repository.get_by_user_id(user_id)

    async def get_latest_resume(self, user_id: str) -> Optional[Resume]:
        """
        Get the most recent resume for a user.

        Args:
            user_id: User ID

        Returns:
            Optional[Resume]: Most recent resume if found, None otherwise
        """
        return await self.resume_repository.get_latest_by_user_id(user_id)

    async def create_resume(
        self, user_id: str, title: str, template_id: str = "default"
    ) -> Resume:
        """
        Create a new resume.

        Args:
            user_id: User ID
            title: Resume title
            template_id: Template ID

        Returns:
            Resume: Created resume

        Raises:
            NotFoundException: If user not found
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            self.logger.warning(f"User not found: {user_id}")
            raise NotFoundException("User not found")

        resume = Resume(
            user=user,
            title=title,
            template_id=template_id,
        )

        created_resume = await self.resume_repository.create(resume)
        self.logger.info(f"Resume created: {created_resume.id} for user {user_id}")

        return created_resume

    async def update_resume(
        self, resume_id: str, user_id: str, update_data: Dict
    ) -> Resume:
        """
        Update a resume.

        Args:
            resume_id: Resume ID
            user_id: User ID
            update_data: Resume data to update

        Returns:
            Resume: Updated resume

        Raises:
            NotFoundException: If resume not found or doesn't belong to user
        """
        resume = await self.get_resume_by_id(resume_id, user_id)

        # Update resume fields
        for key, value in update_data.items():
            if hasattr(resume, key) and key != "id" and key != "user":
                setattr(resume, key, value)

        updated_resume = await self.resume_repository.update(resume_id, resume)
        if not updated_resume:
            self.logger.error(f"Failed to update resume: {resume_id}")
            raise NotFoundException("Resume not found")

        self.logger.info(f"Resume updated: {resume_id}")
        return updated_resume

    async def delete_resume(self, resume_id: str, user_id: str) -> bool:
        """
        Delete a resume.

        Args:
            resume_id: Resume ID
            user_id: User ID

        Returns:
            bool: True if successful, False otherwise

        Raises:
            NotFoundException: If resume not found or doesn't belong to user
        """
        resume = await self.get_resume_by_id(resume_id, user_id)

        result = await self.resume_repository.delete(resume_id)
        if result:
            self.logger.info(f"Resume deleted: {resume_id}")
        else:
            self.logger.error(f"Failed to delete resume: {resume_id}")
            raise NotFoundException("Resume not found")

        return result

    async def create_resume_version(
        self, resume_id: str, user_id: str, title: Optional[str] = None
    ) -> Resume:
        """
        Create a new version of an existing resume.

        Args:
            resume_id: Resume ID
            user_id: User ID
            title: New resume title

        Returns:
            Resume: New resume version

        Raises:
            NotFoundException: If resume not found or doesn't belong to user
        """
        # Verify resume exists and belongs to user
        await self.get_resume_by_id(resume_id, user_id)

        new_resume = await self.resume_repository.create_version(resume_id, title)
        if not new_resume:
            self.logger.error(f"Failed to create resume version: {resume_id}")
            raise NotFoundException("Resume not found")

        self.logger.info(f"Resume version created: {new_resume.id} from {resume_id}")
        return new_resume

    async def filter_resumes(
        self, user_id: str, filter_params: ResumeFilter
    ) -> List[Resume]:
        """
        Filter resumes by parameters.

        Args:
            user_id: User ID
            filter_params: Filter parameters

        Returns:
            List[Resume]: List of filtered resumes

        Raises:
            NotFoundException: If user not found
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            self.logger.warning(f"User not found: {user_id}")
            raise NotFoundException("User not found")

        return await self.resume_repository.get_by_filter(user, filter_params)
