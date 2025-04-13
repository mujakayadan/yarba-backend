"""Cover letter repository implementation."""

from datetime import datetime, timezone
from typing import List, Optional

from beanie import PydanticObjectId
from pydantic import BaseModel

from ..models.cover_letter import CoverLetter
from ..models.user import User
from .base_repository import BeanieRepository


class CoverLetterFilter(BaseModel):
    """Repository filter model for database queries.

    This class is used internally by the repository to filter cover letters
    in the database. It is different from the API-level CoverLetterFilter
    which is used for API request validation.
    """

    template_id: Optional[str] = None
    version: Optional[int] = None
    title_contains: Optional[str] = None
    profile_id: Optional[PydanticObjectId] = None
    portfolio_id: Optional[PydanticObjectId] = None
    resume_id: Optional[PydanticObjectId] = None


class CoverLetterRepository(BeanieRepository[CoverLetter]):
    """Cover letter repository implementation."""

    def __init__(self):
        super().__init__(CoverLetter)

    async def get_by_user_id(self, user_id: PydanticObjectId) -> List[CoverLetter]:
        """
        Get all cover letters belonging to a user.

        Args:
            user_id: User ID

        Returns:
            List of cover letters
        """
        return await self.model_class.find({"user_id": user_id}).to_list()

    async def get_latest_by_user_id(
        self, user_id: PydanticObjectId
    ) -> Optional[CoverLetter]:
        """
        Get the most recent cover letter for a user.

        Args:
            user_id: User ID

        Returns:
            Most recent cover letter or None
        """
        results = (
            await self.model_class.find({"user_id": user_id})
            .sort([("created_at", -1)])
            .limit(1)
            .to_list()
        )
        return results[0] if results else None

    async def get_by_resume_id(self, resume_id: PydanticObjectId) -> List[CoverLetter]:
        """
        Get all cover letters for a specific resume.

        Args:
            resume_id: Resume ID

        Returns:
            List of cover letters based on the resume
        """
        return await self.model_class.find({"resume_id": resume_id}).to_list()

    async def get_by_filter(
        self, user: User, filter_params: CoverLetterFilter
    ) -> List[CoverLetter]:
        """
        Get cover letters by filter criteria.

        Args:
            user: User to filter by
            filter_params: Filter parameters

        Returns:
            List of filtered cover letters
        """
        query = {"user_id": user.id}

        # Add filter parameters to query if they exist
        if filter_params.template_id:
            query["template_id"] = filter_params.template_id

        if filter_params.version is not None:
            query["version"] = filter_params.version

        if filter_params.profile_id:
            query["profile_id"] = PydanticObjectId(filter_params.profile_id)

        if filter_params.portfolio_id:
            query["portfolio_id"] = PydanticObjectId(filter_params.portfolio_id)

        if filter_params.resume_id:
            query["resume_id"] = PydanticObjectId(filter_params.resume_id)

        if filter_params.title_contains:
            query["title"] = {"$regex": filter_params.title_contains, "$options": "i"}

        return await self.model_class.find(query).to_list()

    async def update_metadata(
        self, cover_letter_id: PydanticObjectId, **kwargs
    ) -> Optional[CoverLetter]:
        """
        Update cover letter metadata.

        Args:
            cover_letter_id: Cover letter ID
            **kwargs: Fields to update

        Returns:
            Updated cover letter or None if not found
        """
        cover_letter = await self.get_by_id(cover_letter_id)
        if not cover_letter:
            return None

        # Update fields
        for key, value in kwargs.items():
            if hasattr(cover_letter, key):
                setattr(cover_letter, key, value)

        # Update updated_at field
        cover_letter.updated_at = datetime.now(timezone.utc)

        # Save changes
        await cover_letter.save()
        return cover_letter

    async def update_pdf_key(
        self, cover_letter_id: PydanticObjectId, pdf_key: str
    ) -> bool:
        """
        Update cover letter PDF key.

        Args:
            cover_letter_id: Cover letter ID
            pdf_key: S3 key for the PDF

        Returns:
            bool: True if successful, False otherwise
        """
        cover_letter = await self.get_by_id(cover_letter_id)
        if not cover_letter:
            return False

        cover_letter.cover_letter_pdf_key = pdf_key
        cover_letter.updated_at = datetime.now(timezone.utc)
        await cover_letter.save()
        return True


async def get_cover_letter_repository() -> CoverLetterRepository:
    """Get a cover letter repository.

    Returns:
        CoverLetterRepository: Cover letter repository instance
    """
    return CoverLetterRepository()
