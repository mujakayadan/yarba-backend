"""Resume service for resume management and generation."""

import logging
from typing import Dict, List, Optional

from beanie import PydanticObjectId

from ..exceptions.base import NotFoundException
from ..models.resume import Resume
from ..repositories.resume_repository import ResumeFilter, ResumeRepository
from ..repositories.user_repository import UserRepository

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

    def _generate_proper_title(self, company_name: str, job_title: str) -> str:
        """
        Generate a properly formatted title from company_name and job_title.

        Args:
            company_name: Company name with lowercase and underscores
            job_title: Job title with lowercase and underscores

        Returns:
            Properly formatted title
        """
        if not company_name and not job_title:
            return "My Resume"

        # Convert underscores to spaces and capitalize words
        formatted_company = (
            " ".join(word.capitalize() for word in company_name.split("_"))
            if company_name
            else ""
        )
        formatted_job = (
            " ".join(word.capitalize() for word in job_title.split("_"))
            if job_title
            else ""
        )

        # Combine them with a space if both exist
        if formatted_company and formatted_job:
            return f"{formatted_company} {formatted_job}"
        elif formatted_company:
            return formatted_company
        else:
            return formatted_job

    async def get_resume_by_id(
        self, resume_id: PydanticObjectId, user_id: PydanticObjectId
    ) -> Resume:
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

        if not resume:
            self.logger.warning(f"Resume not found: {resume_id}")
            raise NotFoundException("Resume not found")

        # Check if the resume belongs to the user
        # Use user_id field directly instead of going through the Link object
        if resume.user_id != user_id:
            self.logger.warning(
                f"Access denied: Resume {resume_id} does not belong to user {user_id}"
            )
            raise NotFoundException("Resume not found")

        return resume

    async def get_resumes_by_user(self, user_id: PydanticObjectId) -> List[Resume]:
        """
        Get all resumes for a user.

        Args:
            user_id: User ID

        Returns:
            List[Resume]: List of resumes
        """
        return await self.resume_repository.get_by_user_id(user_id)

    async def get_latest_resume(self, user_id: PydanticObjectId) -> Optional[Resume]:
        """
        Get the most recent resume for a user.

        Args:
            user_id: User ID

        Returns:
            Optional[Resume]: Most recent resume if found, None otherwise
        """
        return await self.resume_repository.get_latest_by_user_id(user_id)

    async def create_resume(
        self,
        user_id: PydanticObjectId,
        profile_id: PydanticObjectId = None,
        portfolio_id: PydanticObjectId = None,
        company_name: Optional[str] = None,
        job_title: Optional[str] = None,
        job_description: Optional[str] = None,
        template_id: Optional[str] = None,
    ) -> Resume:
        """
        Create a new resume.

        Args:
            user_id: User ID
            profile_id: Profile ID
            portfolio_id: Portfolio ID
            company_name: Company name (optional)
            job_title: Job title (optional)
            job_description: Job description (optional)
            template_id: Template ID (optional)

        Returns:
            Resume: Created resume

        Raises:
            NotFoundException: If user not found
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            self.logger.warning(f"User not found: {user_id}")
            raise NotFoundException("User not found")

        # Always generate title from company_name and job_title
        title = self._generate_proper_title(company_name or "", job_title or "")

        # Create a new resume with required fields
        resume = Resume(
            user_id=user_id,
            profile_id=profile_id,
            portfolio_id=portfolio_id,
            title=title,
            version=1,
            template_id=template_id or "default",
            company_name=company_name or "",
            job_title=job_title or "",
            job_description=job_description or "",
            content={},
            custom_sections=[],
            resume_pdf=b"",
        )

        created_resume = await self.resume_repository.create(resume)

        self.logger.info(f"Resume created: {created_resume.id} for user {user_id}")

        return created_resume

    async def update_resume(
        self, resume_id: PydanticObjectId, user_id: PydanticObjectId, update_data: Dict
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

        # Remove title from update_data if present - title should never be directly set
        if "title" in update_data:
            del update_data["title"]

        # Check if company_name or job_title are being updated
        if "company_name" in update_data or "job_title" in update_data:
            # Get the new values or use existing ones
            company_name = update_data.get("company_name", resume.company_name)
            job_title = update_data.get("job_title", resume.job_title)
            # Generate the new title
            update_data["title"] = self._generate_proper_title(company_name, job_title)
            self.logger.info(f"Updated title to: {update_data['title']}")

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

    async def delete_resume(
        self, resume_id: PydanticObjectId, user_id: PydanticObjectId
    ) -> bool:
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
        self,
        resume_id: PydanticObjectId,
        user_id: PydanticObjectId,
        title: Optional[str] = None,
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
        self, user_id: PydanticObjectId, filter_params: ResumeFilter
    ) -> List[Resume]:
        """
        Filter resumes by parameters.

        Args:
            user_id: User ID
            filter_params: Filter parameters (from API schema)

        Returns:
            List[Resume]: List of filtered resumes

        Raises:
            NotFoundException: If user not found
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            self.logger.warning(f"User not found: {user_id}")
            raise NotFoundException("User not found")

        # Convert API schema filter to repository filter
        from core.repositories.resume_repository import ResumeFilter as RepositoryFilter

        # Create an empty repository filter
        repo_filter = RepositoryFilter()

        # Map API filter fields to repository filter fields when they exist
        if (
            hasattr(filter_params, "template_id")
            and filter_params.template_id is not None
        ):
            repo_filter.template_id = filter_params.template_id

        if hasattr(filter_params, "version") and filter_params.version is not None:
            repo_filter.version = filter_params.version

        if hasattr(filter_params, "title") and filter_params.title:
            repo_filter.title_contains = filter_params.title

        # Get all resumes with the repository filter
        resumes = await self.resume_repository.get_by_filter(user, repo_filter)

        # Apply sorting based on sort_by parameter
        if hasattr(filter_params, "sort_by") and filter_params.sort_by:
            sort_option = filter_params.sort_by

            if sort_option == "updated_desc":
                resumes.sort(key=lambda x: x.updated_at, reverse=True)
            elif sort_option == "updated_asc":
                resumes.sort(key=lambda x: x.updated_at)
            elif sort_option == "created_desc":
                resumes.sort(key=lambda x: x.created_at, reverse=True)
            elif sort_option == "created_asc":
                resumes.sort(key=lambda x: x.created_at)
            elif sort_option == "title_asc":
                resumes.sort(key=lambda x: x.title)
            elif sort_option == "title_desc":
                resumes.sort(key=lambda x: x.title, reverse=True)
        else:
            # Default to sort by updated_at in descending order (newest first)
            resumes.sort(key=lambda x: x.updated_at, reverse=True)

        return resumes

    async def count_resumes(
        self, user_id: PydanticObjectId, filter_params: ResumeFilter
    ) -> int:
        """
        Count the total number of resumes matching filter criteria.

        Args:
            user_id: User ID
            filter_params: Filter parameters (from API schema)

        Returns:
            int: Total count of matching resumes

        Raises:
            NotFoundException: If user not found
        """
        # Reuse the filter_resumes method to get all matching resumes
        resumes = await self.filter_resumes(user_id, filter_params)
        return len(resumes)
