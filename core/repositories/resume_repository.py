"""Resume repository implementation."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from beanie import PydanticObjectId
from pydantic import BaseModel

from ..models.portfolio import Portfolio
from ..models.profile import Profile
from ..models.resume import LLMSettings, Resume
from ..models.user import User
from .base_repository import BeanieRepository


class ResumeFilter(BaseModel):
    """Filter model for resume queries."""

    template_id: Optional[str] = None
    version: Optional[int] = None
    title_contains: Optional[str] = None
    profile_id: Optional[str] = None
    portfolio_id: Optional[str] = None


class ResumeRepository(BeanieRepository[Resume]):
    """Repository for Resume documents."""

    def __init__(self):
        """Initialize the repository."""
        super().__init__(Resume)

    async def get_user(self, resume_id: str) -> Optional[User]:
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

    async def get_profile(self, resume_id: str) -> Optional[Profile]:
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

    async def get_portfolio(self, resume_id: str) -> Optional[Portfolio]:
        """
        Get the portfolio associated with a resume.

        Args:
            resume_id: Resume ID

        Returns:
            Optional[Portfolio]: Portfolio if found, None otherwise
        """
        resume = await Resume.get(resume_id)
        if not resume or not resume.portfolio_id:
            return None

        if not resume.portfolio:
            resume.portfolio = await Portfolio.get(resume.portfolio_id)
        return resume.portfolio

    async def get_related_documents(
        self, resume_id: str
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

        # Get portfolio if it exists
        if resume.portfolio_id and not resume.portfolio:
            resume.portfolio = await Portfolio.get(resume.portfolio_id)
        portfolio = resume.portfolio

        return user, profile, portfolio

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

    async def get_by_profile_id(self, profile_id: str) -> List[Resume]:
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

    async def get_by_portfolio_id(self, portfolio_id: str) -> List[Resume]:
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

    async def get_by_filter(
        self, user: User, filter_params: ResumeFilter
    ) -> List[Resume]:
        """
        Get resumes by filter parameters.

        Args:
            user: User
            filter_params: Filter parameters

        Returns:
            List[Resume]: List of resumes
        """
        query = {"user_id": user.id}

        if filter_params.template_id:
            query["template_id"] = filter_params.template_id

        if filter_params.version is not None:
            query["version"] = filter_params.version

        if filter_params.profile_id:
            query["profile_id"] = filter_params.profile_id

        if filter_params.portfolio_id:
            query["portfolio_id"] = filter_params.portfolio_id

        if filter_params.title_contains:
            query["title"] = {"$regex": filter_params.title_contains, "$options": "i"}

        return await Resume.find(query).to_list()

    async def update_content(self, resume_id: str, content: Dict[str, Any]) -> bool:
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

    async def update_pdf(self, resume_id: str, pdf_data: bytes) -> bool:
        """
        Update resume PDF.

        Args:
            resume_id: Resume ID
            pdf_data: PDF data

        Returns:
            bool: True if successful, False otherwise
        """
        result = await Resume.find_one({"_id": resume_id})
        if not result:
            return False

        result.resume_pdf = pdf_data
        result.updated_at = datetime.now(timezone.utc)
        await result.save()
        return True

    async def update_cover_letter(
        self, resume_id: str, content: str, pdf_data: Optional[bytes] = None
    ) -> bool:
        """
        Update cover letter content and PDF.

        Args:
            resume_id: Resume ID
            content: Cover letter content
            pdf_data: Cover letter PDF data

        Returns:
            bool: True if successful, False otherwise
        """
        result = await Resume.find_one({"_id": resume_id})
        if not result:
            return False

        result.cover_letter_content = content
        if pdf_data:
            result.cover_letter_pdf = pdf_data
        result.updated_at = datetime.now(timezone.utc)
        await result.save()
        return True

    async def update_portfolio(self, resume_id: str, portfolio_id: str) -> bool:
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

    async def create_version(
        self, resume_id: str, title: Optional[str] = None
    ) -> Optional[Resume]:
        """
        Create a new version of a resume.

        Args:
            resume_id: Resume ID
            title: New resume title

        Returns:
            Optional[Resume]: New resume version if successful, None otherwise
        """
        original = await Resume.find_one({"_id": resume_id})
        if not original:
            return None

        # Create a new resume with incremented version
        new_resume = Resume(
            user_id=original.user_id,
            profile_id=original.profile_id,
            portfolio_id=original.portfolio_id,
            title=title or original.title,
            version=original.version + 1,
            template_id=original.template_id,
            company_name=original.company_name,
            job_title=original.job_title,
            job_description=original.job_description,
            content=original.content,
            custom_sections=original.custom_sections,
            llm_settings=original.llm_settings,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        await new_resume.create()
        return new_resume

    async def create_for_user(
        self,
        user: User,
        profile_id: str,
        portfolio_id: Optional[str] = None,
        title: str = "My Resume",
    ) -> Resume:
        """
        Create a new resume for a user.

        Args:
            user: User
            profile_id: Profile ID
            portfolio_id: Portfolio ID
            title: Resume title

        Returns:
            Resume: Created resume
        """
        resume = Resume(
            user_id=user.id,
            profile_id=profile_id,
            portfolio_id=portfolio_id,
            title=title,
            version=1,
            content={},
            custom_sections=[],
            llm_settings=LLMSettings(
                model_type="Claude",
                model_name="claude-3-5-sonnet-20240620",
                temperature=0.1,
                p_value=0.9,
                max_tokens=4000,
                system_prompt_version="v2.3",
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await resume.create()
        return resume


async def get_resume_repository(self) -> ResumeRepository:
    """
    Get the resume repository.
    """
    return ResumeRepository()
