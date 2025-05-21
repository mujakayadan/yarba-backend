"""Resume repository implementation."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from beanie import PydanticObjectId

from config.logging_config import get_logger
from config.settings import settings

from ..models.portfolio import Portfolio
from ..models.profile import Profile
from ..models.resume import LLMSettings, Resume
from ..models.user import User
from .base_repository import BeanieRepository


class ResumeRepository(BeanieRepository[Resume]):
    """Repository for Resume documents."""

    def __init__(self):
        """Initialize the repository."""
        super().__init__(Resume)
        self.logger = get_logger(__name__)

    async def get_user(self, resume_id: PydanticObjectId) -> Optional[User]:
        """
        Get the user associated with a resume.

        Args:
            resume_id: Resume ID

        Returns:
            Optional[User]: User if found, None otherwise
        """
        resume = await Resume.get(resume_id)
        if not resume:
            return None

        if not resume.user:
            resume.user = await User.get(resume.user_id)
        return resume.user

    async def get_profile(self, resume_id: PydanticObjectId) -> Optional[Profile]:
        """
        Get the profile associated with a resume.

        Args:
            resume_id: Resume ID

        Returns:
            Optional[Profile]: Profile if found, None otherwise
        """
        resume = await Resume.get(resume_id)
        if not resume:
            return None

        if not resume.profile:
            resume.profile = await Profile.get(resume.profile_id)
        return resume.profile

    async def get_portfolio(self, resume_id: PydanticObjectId) -> Optional[Portfolio]:
        """
        Get the portfolio associated with a resume.

        Args:
            resume_id: Resume ID

        Returns:
            Optional[Portfolio]: Portfolio if found, None otherwise
        """
        resume = await Resume.get(resume_id)
        if not resume:
            return None

        if not resume.portfolio:
            resume.portfolio = await Portfolio.get(resume.portfolio_id)
        return resume.portfolio

    async def get_related_documents(
        self, resume_id: PydanticObjectId
    ) -> Tuple[Optional[User], Optional[Profile], Optional[Portfolio]]:
        """
        Get all related documents (user, profile, portfolio) for a resume in a single call.

        Args:
            resume_id: Resume ID

        Returns:
            Tuple containing User, Profile, and Portfolio (any may be None if not found)
        """
        resume = await Resume.get(resume_id)
        if not resume:
            return None, None, None

        user = profile = portfolio = None

        # Get user
        if not resume.user:
            resume.user = await User.get(resume.user_id)
        user = resume.user

        # Get profile
        if not resume.profile:
            resume.profile = await Profile.get(resume.profile_id)
        profile = resume.profile

        # Get portfolio
        if not resume.portfolio:
            resume.portfolio = await Portfolio.get(resume.portfolio_id)
        portfolio = resume.portfolio

        return user, profile, portfolio

    async def exists(self, resume_id: PydanticObjectId) -> bool:
        """
        Check if a resume with the given ID exists.

        Args:
            resume_id: Resume ID to check

        Returns:
            bool: True if resume exists, False otherwise
        """
        resume = await Resume.get(resume_id)
        return resume is not None

    async def get_by_user(self, user: User) -> List[Resume]:
        """
        Get all resumes for a user.

        Args:
            user: User

        Returns:
            List[Resume]: List of resumes
        """
        return await Resume.find({"user_id": user.id}).to_list()

    async def get_by_user_id(self, user_id: PydanticObjectId) -> List[Resume]:
        """
        Get all resumes for a user by user ID.

        Args:
            user_id: User ID

        Returns:
            List[Resume]: List of resumes
        """
        return await Resume.find({"user_id": user_id}).to_list()

    async def get_by_profile(self, profile: Profile) -> List[Resume]:
        """
        Get all resumes for a profile.

        Args:
            profile: Profile

        Returns:
            List[Resume]: List of resumes
        """
        return await Resume.find({"profile_id": profile.id}).to_list()

    async def get_by_profile_id(self, profile_id: PydanticObjectId) -> List[Resume]:
        """
        Get all resumes for a profile by profile ID.

        Args:
            profile_id: Profile ID

        Returns:
            List[Resume]: List of resumes
        """
        return await Resume.find({"profile_id": profile_id}).to_list()

    async def get_by_portfolio(self, portfolio: Portfolio) -> List[Resume]:
        """
        Get all resumes for a portfolio.

        Args:
            portfolio: Portfolio

        Returns:
            List[Resume]: List of resumes
        """
        return await Resume.find({"portfolio_id": portfolio.id}).to_list()

    async def get_by_portfolio_id(self, portfolio_id: PydanticObjectId) -> List[Resume]:
        """
        Get all resumes for a portfolio by portfolio ID.

        Args:
            portfolio_id: Portfolio ID

        Returns:
            List[Resume]: List of resumes
        """
        return await Resume.find({"portfolio_id": portfolio_id}).to_list()

    async def get_latest_by_user(self, user: User) -> Optional[Resume]:
        """
        Get the latest resume for a user.

        Args:
            user: User

        Returns:
            Optional[Resume]: Latest resume if found, None otherwise
        """
        resumes = (
            await Resume.find({"user_id": user.id}).sort("created_at", -1).to_list()
        )
        return resumes[0] if resumes else None

    async def get_latest_by_user_id(
        self, user_id: PydanticObjectId
    ) -> Optional[Resume]:
        """
        Get the latest resume for a user by user ID.

        Args:
            user_id: User ID

        Returns:
            Optional[Resume]: Latest resume if found, None otherwise
        """
        resumes = (
            await Resume.find({"user_id": user_id}).sort("created_at", -1).to_list()
        )
        return resumes[0] if resumes else None

    async def get_by_template(self, template_id: PydanticObjectId) -> List[Resume]:
        """
        Get all resumes for a template.

        Args:
            template_id: Template ID

        Returns:
            List[Resume]: List of resumes
        """
        return await Resume.find({"template_id": template_id}).to_list()

    def _build_filter_query(self, filter_conditions: Dict[str, Any]) -> Dict[str, Any]:
        query = {}
        search_term = filter_conditions.pop(
            "search_term", None
        )  # Remove search_term to handle separately

        for key, value in filter_conditions.items():
            if value is not None:
                if key == "user_id" and isinstance(value, str):
                    query[key] = PydanticObjectId(value)
                elif (
                    key == "title"
                ):  # Assuming exact match for title if not using search_term
                    query[key] = value
                # Add other specific field handling if needed
                else:
                    query[key] = value

        if search_term:
            # MongoDB text search. Ensure a text index exists on these fields.
            # Example: db.resume.createIndex({ "title": "text", "company_name": "text", "job_title": "text", "job_description": "text" })
            # Alternatively, use $or with $regex for more control if text index is not preferred or for partial matching.
            query["$or"] = [
                {"title": {"$regex": search_term, "$options": "i"}},
                {"company_name": {"$regex": search_term, "$options": "i"}},
                {"job_title": {"$regex": search_term, "$options": "i"}},
                {
                    "job_description": {"$regex": search_term, "$options": "i"}
                },  # Ensure top-level job_description is searched
            ]
            # If a text index is set up and preferred:
            # query["$text"] = {"$search": search_term}

        self.logger.debug(f"Constructed filter query: {query}")
        return query

    async def filter_resumes(
        self,
        filter_conditions: Dict[str, Any],
        sort_field: str,
        sort_direction: int,
        skip: int,
        limit: int,
    ) -> List[Resume]:
        """
        Filter resumes based on a dictionary of conditions, with sorting and pagination.
        If a search_term is provided, results are prioritized by field match.
        """
        search_term = filter_conditions.get(
            "search_term"
        )  # Check if search_term is present

        if search_term:
            # Build the initial match query (excluding search_term itself for the $match stage,
            # as $or with $regex will handle the search part)
            base_match_query = {}
            for key, value in filter_conditions.items():
                if key != "search_term" and value is not None:
                    if key == "user_id" and isinstance(value, str):
                        base_match_query[key] = PydanticObjectId(value)
                    else:
                        base_match_query[key] = value

            # Add the $or condition for the search term to the base match query
            base_match_query["$or"] = [
                {"title": {"$regex": search_term, "$options": "i"}},
                {"company_name": {"$regex": search_term, "$options": "i"}},
                {"job_title": {"$regex": search_term, "$options": "i"}},
                {"job_description": {"$regex": search_term, "$options": "i"}},
            ]

            self.logger.info(
                f"Filtering resumes with search_term '{search_term}' using aggregation. Base match: {base_match_query}"
            )

            # Ensure search_term is treated as a string for the regex in aggregation
            # and escape any special regex characters from the user input to be safe
            import re

            safe_search_term_for_regex = re.escape(search_term)

            pipeline = [
                {"$match": base_match_query},
                {
                    "$addFields": {
                        "match_priority": {
                            "$switch": {
                                "branches": [
                                    {
                                        "case": {
                                            "$regexMatch": {
                                                "input": "$company_name",
                                                "regex": safe_search_term_for_regex,
                                                "options": "i",
                                            }
                                        },
                                        "then": 1,
                                    },
                                    {
                                        "case": {
                                            "$regexMatch": {
                                                "input": "$job_title",
                                                "regex": safe_search_term_for_regex,
                                                "options": "i",
                                            }
                                        },
                                        "then": 2,
                                    },
                                    {
                                        "case": {
                                            "$regexMatch": {
                                                "input": "$job_description",
                                                "regex": safe_search_term_for_regex,
                                                "options": "i",
                                            }
                                        },
                                        "then": 3,
                                    },
                                    {
                                        "case": {
                                            "$regexMatch": {
                                                "input": "$title",
                                                "regex": safe_search_term_for_regex,
                                                "options": "i",
                                            }
                                        },
                                        "then": 4,
                                    },
                                ],
                                "default": 5,  # Should not be hit if $match is correct
                            }
                        }
                    }
                },
                {"$sort": {"match_priority": 1, sort_field: sort_direction}},
                {"$skip": skip},
                {"$limit": limit},
                # Optionally, remove the match_priority field from the output
                # {"$project": {"match_priority": 0}}
            ]
            self.logger.debug(f"Resume aggregation pipeline: {pipeline}")
            # Let Beanie parse the aggregation results into Resume model instances
            resumes = await Resume.aggregate(pipeline, projection_model=Resume).to_list(
                length=limit
            )
        else:
            # No search_term, use the simpler find query
            query = self._build_filter_query(filter_conditions)
            self.logger.info(
                f"Filtering resumes (no search_term) with query: {query}, sort: {sort_field} {sort_direction}, skip: {skip}, limit: {limit}"
            )
            resumes = (
                await Resume.find(query)
                .sort([(sort_field, sort_direction)])
                .skip(skip)
                .limit(limit)
                .to_list()
            )
        return resumes

    async def count_documents(self, filter_conditions: Dict[str, Any]) -> int:
        """
        Count documents matching the filter conditions.
        """
        query = self._build_filter_query(filter_conditions)
        self.logger.info(f"Counting resumes with query: {query}")
        return await Resume.find(query).count()

    async def update_content(
        self, resume_id: PydanticObjectId, content: Dict[str, Any]
    ) -> bool:
        """
        Update resume content.

        Args:
            resume_id: Resume ID
            content: Updated content

        Returns:
            bool: True if successful, False otherwise
        """
        result = await Resume.find_one({"_id": resume_id})
        if not result:
            return False

        result.content = content
        result.updated_at = datetime.now(timezone.utc)
        await result.save()
        return True

    async def update_pdf_key(self, resume_id: PydanticObjectId, pdf_key: str) -> bool:
        """
        Update resume PDF key.

        Args:
            resume_id: Resume ID
            pdf_key: S3 key for the PDF

        Returns:
            bool: True if successful, False otherwise
        """
        result = await Resume.find_one({"_id": resume_id})
        if not result:
            return False

        result.resume_pdf_key = pdf_key
        result.updated_at = datetime.now(timezone.utc)
        await result.save()
        return True

    async def update_cover_letter(
        self,
        resume_id: PydanticObjectId,
        content: str,
    ) -> bool:
        """
        Update cover letter content.

        Args:
            resume_id: Resume ID
            content: Cover letter content

        Returns:
            bool: True if successful, False otherwise
        """
        result = await Resume.find_one({"_id": resume_id})
        if not result:
            return False

        result.cover_letter_content = content
        result.updated_at = datetime.now(timezone.utc)
        await result.save()
        return True

    async def update_portfolio(
        self, resume_id: PydanticObjectId, portfolio_id: PydanticObjectId
    ) -> bool:
        """
        Update resume portfolio.

        Args:
            resume_id: Resume ID
            portfolio_id: Portfolio ID

        Returns:
            bool: True if successful, False otherwise
        """
        result = await Resume.find_one({"_id": resume_id})
        if not result:
            return False

        result.portfolio_id = portfolio_id
        result.updated_at = datetime.now(timezone.utc)
        await result.save()
        return True

    async def create_for_user(
        self,
        user: User,
        profile_id: PydanticObjectId,
        portfolio_id: Optional[PydanticObjectId] = None,
        title: str = "My Resume",
        template_id: Optional[str] = None,
    ) -> Resume:
        """
        Create a new resume for a user.

        Args:
            user: User
            profile_id: Profile ID
            portfolio_id: Portfolio ID
            title: Resume title
            template_id: Optional template ID

        Returns:
            Resume: Created resume
        """
        resume = Resume(
            user_id=user.id,
            profile_id=profile_id,
            portfolio_id=portfolio_id,
            title=title,
            template_id=template_id,
            content={},
            custom_sections=[],
            llm_settings=LLMSettings(
                model_name=settings.llm.default_model,
                temperature=settings.llm.temperature,
                max_tokens=settings.llm.max_tokens,
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await resume.create()
        return resume

    async def add_cover_letter(
        self, resume_id: PydanticObjectId, cover_letter_id: PydanticObjectId
    ) -> bool:
        """
        Add a cover letter ID to a resume's cover_letter_ids list.

        Args:
            resume_id: Resume ID
            cover_letter_id: Cover letter ID to add

        Returns:
            bool: True if successful, False otherwise
        """
        resume = await Resume.get(resume_id)
        if not resume:
            return False

        # Add cover letter ID to resume's list if not already there
        if not hasattr(resume, "cover_letter_ids"):
            resume.cover_letter_ids = []

        if cover_letter_id not in resume.cover_letter_ids:
            resume.cover_letter_ids.append(cover_letter_id)
            resume.updated_at = datetime.now(timezone.utc)
            await resume.save()
            return True

        return True  # Already in the list

    async def remove_cover_letter(
        self, resume_id: PydanticObjectId, cover_letter_id: PydanticObjectId
    ) -> bool:
        """
        Remove a cover letter ID from a resume's cover_letter_ids list.

        Args:
            resume_id: Resume ID
            cover_letter_id: Cover letter ID to remove

        Returns:
            bool: True if successful, False otherwise
        """
        resume = await Resume.get(resume_id)
        if not resume:
            return False

        # Remove cover letter ID from resume's list if it exists
        if (
            hasattr(resume, "cover_letter_ids")
            and cover_letter_id in resume.cover_letter_ids
        ):
            resume.cover_letter_ids.remove(cover_letter_id)
            resume.updated_at = datetime.now(timezone.utc)
            await resume.save()
            return True

        return True  # Not in the list, so nothing to remove

    async def get_cover_letters(
        self, resume_id: PydanticObjectId
    ) -> List[PydanticObjectId]:
        """
        Get all cover letter IDs associated with a resume.

        Args:
            resume_id: Resume ID

        Returns:
            List[PydanticObjectId]: List of cover letter IDs
        """
        resume = await Resume.get(resume_id)
        if not resume:
            return []

        return resume.cover_letter_ids if hasattr(resume, "cover_letter_ids") else []

    async def update_llm_usage(
        self,
        resume_id: PydanticObjectId,
        tokens_used: int,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        model_name: str,
        operation_type: str,
    ) -> bool:
        """
        Update LLM usage statistics for a specific resume.

        Args:
            resume_id: Resume ID
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
            # Get resume
            resume = await Resume.get(resume_id)
            if not resume:
                self.logger.error(f"Resume not found for ID: {resume_id}")
                return False

            # Get current date
            now = datetime.now(timezone.utc)

            # Initialize if this is first usage
            if not resume.llm_usage.last_used:
                resume.llm_usage.last_used = now

            # Update total usage
            resume.llm_usage.total_tokens += tokens_used
            resume.llm_usage.total_input_tokens += input_tokens
            resume.llm_usage.total_output_tokens += output_tokens
            resume.llm_usage.total_cost += cost
            resume.llm_usage.last_used = now

            # Update usage by model
            if model_name not in resume.llm_usage.usage_by_model:
                resume.llm_usage.usage_by_model[model_name] = {"tokens": 0, "cost": 0.0}
            resume.llm_usage.usage_by_model[model_name]["tokens"] += tokens_used
            resume.llm_usage.usage_by_model[model_name]["cost"] += cost

            # Update usage by operation
            if operation_type not in resume.llm_usage.usage_by_operation:
                resume.llm_usage.usage_by_operation[operation_type] = {
                    "tokens": 0,
                    "cost": 0.0,
                }
            resume.llm_usage.usage_by_operation[operation_type]["tokens"] += tokens_used
            resume.llm_usage.usage_by_operation[operation_type]["cost"] += cost

            # Save changes
            resume.updated_at = now
            await resume.save()
            self.logger.info(
                f"Updated LLM usage for resume_id: {resume_id}, added {tokens_used} tokens, ${cost:.6f}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error updating LLM usage for resume: {e}")
            return False


async def get_resume_repository(self) -> ResumeRepository:
    """
    Get the resume repository.
    """
    return ResumeRepository()
