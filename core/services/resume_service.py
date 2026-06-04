"""Resume service for resume management and generation."""

from datetime import UTC, datetime
from typing import Any

from beanie import PydanticObjectId, SortDirection

from api.schemas.resume import ResumeFilter as ApiResumeFilter
from api.schemas.resume import ResumeSelectionItem, SortOptions
from config.logging_config import get_logger

from ..exceptions.base import NotFoundException
from ..models.resume import Resume, ResumeSelectionProjection
from ..repositories.resume_repository import ResumeRepository
from ..repositories.user_repository import UserRepository
from ..services.job_service import JobService

logger = get_logger(__name__)


class ResumeService:
    """Service for resume operations."""

    def __init__(
        self,
        resume_repository: ResumeRepository,
        user_repository: UserRepository,
        job_service: JobService | None = None,
    ):
        """Initialize the service.

        Args:
            resume_repository: Resume repository instance
            user_repository: User repository instance
            job_service: Job service instance for extracting job information
        """
        self.resume_repository = resume_repository
        self.user_repository = user_repository
        self.job_service = job_service
        self.logger = get_logger(self.__class__.__name__)

    def _parse_sort_option(self, sort_by: str | None) -> tuple[str, int]:
        """Parse the sort_by string into a field name and direction.

        Args:
            sort_by: String like "updated_desc" or "title_asc".

        Returns:
            Tuple of (field_name, direction) e.g., ("updated_at", -1).

        Raises:
            ValueError: If the sort_by string is invalid.
        """
        if not sort_by or not isinstance(sort_by, str):
            # Default sort option if none provided or invalid type
            return "updated_at", -1

        parts = sort_by.lower().split("_")
        if len(parts) != 2:
            raise ValueError(f"Invalid sort_by format: {sort_by}")

        field_part, direction_part = parts

        field_mapping = {
            "updated": "updated_at",
            "created": "created_at",
            "title": "title",
            # Add other mappings if needed
        }

        if field_part not in field_mapping:
            raise ValueError(f"Invalid sort field: {field_part} in {sort_by}")

        db_field = field_mapping[field_part]

        if direction_part == "asc":
            direction = 1
        elif direction_part == "desc":
            direction = -1
        else:
            raise ValueError(f"Invalid sort direction: {direction_part} in {sort_by}")

        return db_field, direction

    def _generate_proper_title(self, company_name: str, job_title: str) -> str:
        """Generate a properly formatted title from company_name and job_title.

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
        """Get a resume by ID.

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

    async def get_resumes_by_user(self, user_id: PydanticObjectId) -> list[Resume]:
        """Get all resumes for a user.

        Args:
            user_id: User ID

        Returns:
            List[Resume]: List of resumes
        """
        return await self.resume_repository.get_by_user_id(user_id)

    async def get_latest_resume(self, user_id: PydanticObjectId) -> Resume | None:
        """Get the most recent resume for a user.

        Args:
            user_id: User ID

        Returns:
            Optional[Resume]: Most recent resume if found, None otherwise
        """
        return await self.resume_repository.get_latest_by_user_id(user_id)

    async def create_resume(
        self,
        user_id: PydanticObjectId,
        profile_id: PydanticObjectId | None = None,
        portfolio_id: PydanticObjectId | None = None,
        company_name: str | None = None,
        job_title: str | None = None,
        job_description: str | None = None,
        job_description_url: str | None = None,
        template_id: str | None = None,
    ) -> Resume:
        """Create a new resume.

        Args:
            user_id: User ID
            profile_id: Profile ID
            portfolio_id: Portfolio ID
            company_name: Company name (optional)
            job_title: Job title (optional)
            job_description: Job description (optional)
            job_description_url: Job description URL (optional)
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
            job_description_url=job_description_url,
            content={},
            custom_sections=[],
        )

        created_resume = await self.resume_repository.create(resume)

        self.logger.info(f"Resume created: {created_resume.id} for user {user_id}")

        return created_resume

    async def update_resume(
        self, resume_id: PydanticObjectId, user_id: PydanticObjectId, update_data: dict
    ) -> Resume:
        """Update an existing resume.

        Args:
            resume_id: Resume ID
            user_id: User ID
            update_data: Dictionary of fields to update

        Returns:
            Resume: Updated resume

        Raises:
            NotFoundException: If resume not found or doesn't belong to user
        """
        resume = await self.get_resume_by_id(resume_id, user_id)

        # Remove title from update_data if present - title should never be directly set
        # and is handled by company_name/job_title changes.
        if "title" in update_data:
            del update_data["title"]

        # Flag to check if any actual update happened that needs saving
        updated_fields = False

        # Check if company_name or job_title are being updated to regenerate title
        new_company_name = update_data.get("company_name")
        new_job_title = update_data.get("job_title")

        # Ensure current_company_name and current_job_title have defaults if None
        current_company_name = resume.company_name or ""
        current_job_title = resume.job_title or ""

        title_needs_update = False
        if new_company_name is not None and new_company_name != current_company_name:
            resume.company_name = new_company_name
            current_company_name = new_company_name  # update for title generation
            updated_fields = True
            title_needs_update = True
        if new_job_title is not None and new_job_title != current_job_title:
            resume.job_title = new_job_title
            current_job_title = new_job_title  # update for title generation
            updated_fields = True
            title_needs_update = True

        if title_needs_update:
            new_title = self._generate_proper_title(
                current_company_name, current_job_title
            )
            if resume.title != new_title:
                resume.title = new_title
                self.logger.info(f"Updated title to: {new_title}")
                updated_fields = True

        # Update other resume fields from update_data
        for key, value in update_data.items():
            # Fields that are handled separately or are protected
            protected_or_handled_fields = [
                "company_name",  # Handled above for title generation
                "job_title",  # Handled above for title generation
                "id",
                "user_id",
                "profile_id",
                "portfolio_id",
                "created_at",
                "updated_at",  # This will be set explicitly if updated_fields is true
                "title",  # Regenerated, not set directly
            ]
            if key not in protected_or_handled_fields:
                if hasattr(resume, key):
                    if getattr(resume, key) != value:
                        setattr(resume, key, value)
                        updated_fields = True
                else:
                    self.logger.warning(
                        f"Attempted to update non-existent field '{key}' on resume {resume_id}"
                    )

        if updated_fields:
            # Explicitly update updated_at timestamp
            resume.updated_at = datetime.now(UTC)
            await (
                resume.save_changes()
            )  # Use Beanie's save_changes for instance updates
            self.logger.info(f"Resume updated and changes saved: {resume_id}")
        else:
            self.logger.info(f"No actual changes to save for resume: {resume_id}")

        return resume

    async def delete_resume(
        self, resume_id: PydanticObjectId, user_id: PydanticObjectId
    ) -> bool:
        """Delete a resume.

        Args:
            resume_id: Resume ID
            user_id: User ID

        Returns:
            bool: True if successful, False otherwise

        Raises:
            NotFoundException: If resume not found or doesn't belong to user
        """
        await self.get_resume_by_id(resume_id, user_id)

        result = await self.resume_repository.delete(resume_id)
        if result:
            self.logger.info(f"Resume deleted: {resume_id}")
        else:
            self.logger.error(f"Failed to delete resume: {resume_id}")
            raise NotFoundException("Resume not found")

        return result

    async def filter_resumes(
        self, user_id: PydanticObjectId, filter_params: ApiResumeFilter
    ) -> list[Resume]:
        """Filter resumes based on provided criteria.

        Args:
            user_id: User ID
            filter_params: ApiResumeFilter object containing filter criteria such as:
                - title (Optional[str]): Filter by title.
                - template_id (Optional[str]): Filter by template ID.
                - is_cover_letter (Optional[bool]): Filter by document type (True for cover letters).
                - sort_by (Optional[str]): Sort field and direction.
                - skip (int): Number of resumes to skip.
                - limit (int): Number of resumes to return.
                - search_term (Optional[str]): Search term for text search.

        Returns:
            List[Resume]: List of resumes matching the filter criteria.

        Raises:
            ValueError: If sort_by is invalid.
        """
        # Convert API filter to repository filter
        repo_filter: dict[str, Any] = {"user_id": user_id}
        if filter_params.title:
            repo_filter["title"] = filter_params.title
        if filter_params.template_id:
            repo_filter["template_id"] = filter_params.template_id
        if filter_params.is_cover_letter is not None:  # Handle boolean False case
            # Assuming 'type' field distinguishes resumes from cover letters
            # This might need adjustment based on your actual model
            repo_filter["type"] = (
                "cover_letter" if filter_params.is_cover_letter else "resume"
            )
        if filter_params.search_term:  # Add this block
            repo_filter["search_term"] = filter_params.search_term

        # Handle sorting
        sort_field, sort_direction = self._parse_sort_option(filter_params.sort_by)

        return await self.resume_repository.filter_resumes(
            filter_conditions=repo_filter,
            sort_field=sort_field,
            sort_direction=sort_direction,
            skip=filter_params.skip,
            limit=filter_params.limit,
        )

    async def count_resumes(
        self, user_id: PydanticObjectId, filter_params: ApiResumeFilter
    ) -> int:
        """Count resumes matching the filter criteria.

        Args:
            user_id: User ID
            filter_params: ApiResumeFilter object containing filter criteria.
                           Includes an optional 'search_term' for text search.

        Returns:
            int: Total number of resumes matching the filter.
        """
        # Convert API filter to repository filter
        repo_filter: dict[str, Any] = {"user_id": user_id}
        if filter_params.title:
            repo_filter["title"] = filter_params.title
        if filter_params.template_id:
            repo_filter["template_id"] = filter_params.template_id
        if filter_params.is_cover_letter is not None:
            repo_filter["type"] = (
                "cover_letter" if filter_params.is_cover_letter else "resume"
            )
        if filter_params.search_term:  # Add this block
            repo_filter["search_term"] = filter_params.search_term

        return await self.resume_repository.count_documents(
            filter_conditions=repo_filter
        )

    async def list_resumes_for_selection(
        self, user_id: PydanticObjectId, sort_by: str = SortOptions.UPDATED_DESC
    ) -> list[ResumeSelectionItem]:
        """List resumes for a user, returning only ID and title, with sorting.

        Args:
            user_id: User ID
            sort_by: Sorting option (e.g., 'updated_desc', 'title_asc')

        Returns:
            List[ResumeSelectionItem]: List of resume IDs and titles.
        """
        self.logger.info(
            f"Listing resumes for selection for user {user_id}, sort_by: {sort_by}"
        )

        sort_criteria: list[tuple[str, SortDirection]] = []
        if sort_by == SortOptions.UPDATED_DESC:
            sort_criteria = [("updated_at", SortDirection.DESCENDING)]
        elif sort_by == SortOptions.UPDATED_ASC:
            sort_criteria = [("updated_at", SortDirection.ASCENDING)]
        elif sort_by == SortOptions.CREATED_DESC:
            sort_criteria = [("created_at", SortDirection.DESCENDING)]
        elif sort_by == SortOptions.CREATED_ASC:
            sort_criteria = [("created_at", SortDirection.ASCENDING)]
        elif sort_by == SortOptions.TITLE_ASC:
            sort_criteria = [("title", SortDirection.ASCENDING)]
        elif sort_by == SortOptions.TITLE_DESC:
            sort_criteria = [("title", SortDirection.DESCENDING)]
        else:  # Default sort if an invalid option is somehow passed
            sort_criteria = [("updated_at", SortDirection.DESCENDING)]

        resumes_data = (
            await Resume.find(
                Resume.user_id == user_id, projection_model=ResumeSelectionProjection
            )
            .sort(*sort_criteria)
            .to_list()
        )

        selection_list = []
        for resume_proj in resumes_data:
            selection_list.append(
                ResumeSelectionItem(
                    id=resume_proj.id,
                    resume_name=resume_proj.title
                    or "Untitled Resume",  # Use title directly
                )
            )

        self.logger.info(
            f"Found {len(selection_list)} resumes for selection for user {user_id}"
        )
        return selection_list
