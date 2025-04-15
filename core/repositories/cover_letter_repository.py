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
    profile_id: Optional[PydanticObjectId] = None
    portfolio_id: Optional[PydanticObjectId] = None
    resume_id: Optional[PydanticObjectId] = None
    skip: Optional[int] = 0
    limit: Optional[int] = 10
    sort_by: Optional[str] = "updated_desc"


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
        Get cover letters by filter parameters with pagination and sorting.

        Args:
            user: User
            filter_params: Filter parameters

        Returns:
            List[CoverLetter]: List of cover letters
        """
        query = {"user_id": user.id}

        if filter_params.profile_id:
            query["profile_id"] = filter_params.profile_id

        if filter_params.portfolio_id:
            query["portfolio_id"] = filter_params.portfolio_id

        if filter_params.template_id:
            query["template_id"] = filter_params.template_id

        if filter_params.resume_id:
            query["resume_id"] = filter_params.resume_id

        # Create query and apply sorting
        cover_letters_query = self.model_class.find(query)

        # Apply sorting based on sort_by parameter
        if filter_params.sort_by:
            sort_option = filter_params.sort_by
            if sort_option == "updated_desc":
                cover_letters_query = cover_letters_query.sort([("updated_at", -1)])
            elif sort_option == "updated_asc":
                cover_letters_query = cover_letters_query.sort([("updated_at", 1)])
            elif sort_option == "created_desc":
                cover_letters_query = cover_letters_query.sort([("created_at", -1)])
            elif sort_option == "created_asc":
                cover_letters_query = cover_letters_query.sort([("created_at", 1)])
            elif sort_option == "template_asc":
                cover_letters_query = cover_letters_query.sort([("template_id", 1)])
            elif sort_option == "template_desc":
                cover_letters_query = cover_letters_query.sort([("template_id", -1)])
        else:
            # Default sort by updated_at desc
            cover_letters_query = cover_letters_query.sort([("updated_at", -1)])

        # Apply pagination
        if filter_params.skip is not None:
            cover_letters_query = cover_letters_query.skip(filter_params.skip)
        if filter_params.limit is not None:
            cover_letters_query = cover_letters_query.limit(filter_params.limit)

        return await cover_letters_query.to_list()

    async def count_by_filter(
        self, user: User, filter_params: CoverLetterFilter
    ) -> int:
        """
        Count cover letters matching filter criteria.

        Args:
            user: User
            filter_params: Filter parameters

        Returns:
            int: Count of matching cover letters
        """
        query = {"user_id": user.id}

        if filter_params.profile_id:
            query["profile_id"] = filter_params.profile_id

        if filter_params.portfolio_id:
            query["portfolio_id"] = filter_params.portfolio_id

        if filter_params.template_id:
            query["template_id"] = filter_params.template_id

        if filter_params.resume_id:
            query["resume_id"] = filter_params.resume_id

        return await self.model_class.find(query).count()

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

    async def update_llm_usage(
        self,
        cover_letter_id: PydanticObjectId,
        tokens_used: int,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        model_name: str,
        operation_type: str,
    ) -> bool:
        """
        Update LLM usage statistics for a specific cover letter.

        Args:
            cover_letter_id: Cover letter ID
            tokens_used: Total number of tokens used in this operation
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            cost: Cost of this LLM operation in USD
            model_name: Name of the LLM model used
            operation_type: Type of operation (e.g., "generation", "extract_job_details")

        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            # Get cover letter
            cover_letter = await CoverLetter.get(cover_letter_id)
            if not cover_letter:
                self.logger.error(f"Cover letter not found for ID: {cover_letter_id}")
                return False

            # Get current date
            now = datetime.now(timezone.utc)

            # Initialize if this is first usage
            if not cover_letter.llm_usage.last_used:
                cover_letter.llm_usage.last_used = now

            # Update total usage
            cover_letter.llm_usage.total_tokens += tokens_used
            cover_letter.llm_usage.total_input_tokens += input_tokens
            cover_letter.llm_usage.total_output_tokens += output_tokens
            cover_letter.llm_usage.total_cost += cost
            cover_letter.llm_usage.last_used = now

            # Update usage by model
            if model_name not in cover_letter.llm_usage.usage_by_model:
                cover_letter.llm_usage.usage_by_model[model_name] = {
                    "tokens": 0,
                    "cost": 0.0,
                }
            cover_letter.llm_usage.usage_by_model[model_name]["tokens"] += tokens_used
            cover_letter.llm_usage.usage_by_model[model_name]["cost"] += cost

            # Update usage by operation
            if operation_type not in cover_letter.llm_usage.usage_by_operation:
                cover_letter.llm_usage.usage_by_operation[operation_type] = {
                    "tokens": 0,
                    "cost": 0.0,
                }
            cover_letter.llm_usage.usage_by_operation[operation_type][
                "tokens"
            ] += tokens_used
            cover_letter.llm_usage.usage_by_operation[operation_type]["cost"] += cost

            # Save changes
            cover_letter.updated_at = now
            await cover_letter.save()
            self.logger.info(
                f"Updated LLM usage for cover_letter_id: {cover_letter_id}, added {tokens_used} tokens, ${cost:.6f}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error updating LLM usage for cover letter: {e}")
            return False


async def get_cover_letter_repository() -> CoverLetterRepository:
    """Get a cover letter repository.

    Returns:
        CoverLetterRepository: Cover letter repository instance
    """
    return CoverLetterRepository()
