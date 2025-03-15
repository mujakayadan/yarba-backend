"""Portfolio and PortfolioItem models for the RBT database."""

from datetime import datetime
from typing import List, Dict, Optional, Any, Union

from beanie import Document, Link, PydanticObjectId
from pydantic import BaseModel, Field, model_validator

from core.models.user import User
from core.models.profile import Profile


class CareerSummary(BaseModel):
    """Career summary information including job titles and experience."""

    job_titles: List[str] = Field(
        default=[],
        description="List of job titles the user has held. The LLM will choose the most suitable one.",
    )
    years_of_experience: str = Field(
        default="", description="Years of experience in the field."
    )
    default_summary: str = Field(
        default="",
        description="Default career summary to use when a custom one is not generated.",
    )

    model_config = {"validate_assignment": True}


class WorkExperience(BaseModel):
    """Work experience entry."""

    job_title: str = Field(default="")
    company: str = Field(default="")
    location: str = Field(default="")
    time: str = Field(default="")
    responsibilities: List[str] = Field(default=[])

    model_config = {"validate_assignment": True}


class Education(BaseModel):
    """Education entry."""

    degree_type: str = Field(default="")
    degree: str = Field(default="")
    university_name: str = Field(default="")
    time: str = Field(default="")
    location: str = Field(default="")
    GPA: str = Field(default="")
    transcript: List[str] = Field(default=[])

    model_config = {"validate_assignment": True}


class Project(BaseModel):
    """Project entry."""

    name: str = Field(default="")
    bullet_points: List[str] = Field(default=[])
    date: str = Field(default="")

    model_config = {"validate_assignment": True}


class Award(BaseModel):
    """Award entry."""

    name: str = Field(default="")
    explanation: str = Field(default="")

    model_config = {"validate_assignment": True}


class Publication(BaseModel):
    """Publication entry."""

    name: str = Field(default="")
    publisher: str = Field(default="")
    link: str = Field(default="")
    time: str = Field(default="")

    model_config = {"validate_assignment": True}


class CustomSections(BaseModel):
    """Custom sections configuration."""

    enabled: List[str] = Field(default=[])
    order: List[str] = Field(default=[])

    model_config = {"validate_assignment": True}


class SkillCategory(BaseModel):
    """Skill category with a list of skills."""

    category: str = Field(default="")
    skills: List[str] = Field(default=[])

    model_config = {"validate_assignment": True}


class Portfolio(Document):
    """Portfolio model for storing professional information."""

    user_id: PydanticObjectId = Field(
        description="ID of the user who owns this portfolio."
    )
    profile_id: Optional[PydanticObjectId] = Field(
        default=None, description="ID of the profile associated with this portfolio."
    )
    user: Optional[Link[User]] = None
    profile: Optional[Link[Profile]] = None

    title: str = Field(default="", description="Title of the portfolio.")
    description: str = Field(default="", description="Description of the portfolio.")
    professional_title: Optional[str] = Field(
        default=None,
        description="Professional title to use. If None, the LLM will choose from job_titles.",
    )

    career_summary: CareerSummary = Field(
        default_factory=CareerSummary,
        description="Career summary information, including multiple job titles and experience.",
    )

    skills: List[Dict[str, List[str]]] = Field(
        default=[], description="List of skill categories and their skills."
    )

    work_experience: List[WorkExperience] = Field(
        default=[], description="List of work experiences."
    )

    education: List[Education] = Field(
        default=[], description="List of education entries."
    )

    projects: List[Project] = Field(default=[], description="List of projects.")

    awards: List[Award] = Field(default=[], description="List of awards.")

    publications: List[Publication] = Field(
        default=[], description="List of publications."
    )

    certifications: List[Any] = Field(default=[], description="List of certifications.")

    custom_sections: CustomSections = Field(
        default_factory=CustomSections, description="Custom sections configuration."
    )

    is_active: bool = Field(
        default=True, description="Whether this portfolio is active."
    )

    version: str = Field(default="1.0", description="Version of the portfolio.")

    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the portfolio was created."
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the portfolio was last updated.",
    )

    async def get_user(self) -> Optional[User]:
        """Get the user associated with this portfolio."""
        if not self.user:
            self.user = await User.get(self.user_id)
        return self.user

    async def get_profile(self) -> Optional[Profile]:
        """Get the profile associated with this portfolio."""
        if self.profile_id and not self.profile:
            self.profile = await Profile.get(self.profile_id)
        return self.profile

    async def get_items(self) -> List["PortfolioItem"]:
        """Get all portfolio items associated with this portfolio."""
        return await PortfolioItem.find({"portfolio_id": self.id}).to_list()

    async def get_items_by_type(self, item_type: str) -> List["PortfolioItem"]:
        """Get portfolio items of a specific type."""
        return await PortfolioItem.find(
            {"portfolio_id": self.id, "type": item_type}
        ).to_list()

    async def get_items_by_tag(self, tag: str) -> List["PortfolioItem"]:
        """Get portfolio items with a specific tag."""
        return await PortfolioItem.find(
            {"portfolio_id": self.id, "tags": tag}
        ).to_list()

    def get_appropriate_job_title(self, job_description: Optional[str] = None) -> str:
        """
        Get the most appropriate job title based on the job description.

        If professional_title is set, it will be returned.
        Otherwise, if job_description is provided, it will be used to select
        the most appropriate job title from the available job titles.
        If no match is found or job_description is None, the first job title
        will be returned, or a default title if no job titles are available.

        Args:
            job_description: Optional job description to match against

        Returns:
            The most appropriate job title
        """
        if self.professional_title:
            return self.professional_title

        if not self.career_summary.job_titles:
            return "Professional"

        # For now, just return the first job title
        # In a real implementation, this would use the LLM to select the most appropriate title
        return self.career_summary.job_titles[0]

    def get_skill_highlights(self, limit: int = 5) -> List[str]:
        """
        Get a list of the most important skills.

        Args:
            limit: Maximum number of skills to return

        Returns:
            List of important skills
        """
        all_skills = []
        for skill_category in self.skills:
            for category, skills in skill_category.items():
                all_skills.extend(skills)

        # In a real implementation, this would use the LLM to select the most important skills
        # For now, just return the first 'limit' skills
        return all_skills[:limit]

    def get_career_summary(self, job_description: Optional[str] = None) -> str:
        """
        Generate a career summary based on the portfolio content.

        If job_description is provided, the summary will be tailored to the job.
        Otherwise, a default summary will be returned.

        Args:
            job_description: Optional job description to tailor the summary to

        Returns:
            A career summary
        """
        job_title = self.get_appropriate_job_title(job_description)
        years_exp = self.career_summary.years_of_experience

        if self.career_summary.default_summary:
            return f"Experienced {job_title} with {years_exp} years of experience {self.career_summary.default_summary}"

        # If no default summary, create a basic one
        skill_highlights = self.get_skill_highlights()
        skills_text = ", ".join(skill_highlights)

        return f"Experienced {job_title} with {years_exp} years of experience. Skilled in {skills_text}."

    model_config = {
        "validate_assignment": True,
        "json_encoders": {datetime: lambda v: v.isoformat()},
        "collection": "portfolios",
    }


class PortfolioItem(Document):
    """Portfolio item model for showcasing specific items in a portfolio."""

    portfolio_id: PydanticObjectId = Field(
        description="ID of the portfolio this item belongs to."
    )
    portfolio: Optional[Link[Portfolio]] = None

    title: str = Field(description="Title of the portfolio item.")
    description: str = Field(
        default="", description="Description of the portfolio item."
    )
    type: str = Field(
        description="Type of portfolio item (e.g., project, work, education)."
    )
    url: str = Field(default="", description="URL associated with the portfolio item.")
    bullet_points: List[str] = Field(
        default=[], description="List of bullet points describing the portfolio item."
    )
    tags: List[str] = Field(
        default=[], description="Tags associated with the portfolio item."
    )
    date: str = Field(
        default="", description="Date associated with the portfolio item."
    )
    order: int = Field(
        default=0, description="Order of the portfolio item in the portfolio."
    )
    is_featured: bool = Field(
        default=False, description="Whether this item is featured in the portfolio."
    )
    company: str = Field(
        default="", description="Company associated with the portfolio item."
    )
    location: str = Field(
        default="", description="Location associated with the portfolio item."
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the portfolio item was created.",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the portfolio item was last updated.",
    )

    async def get_portfolio(self) -> Optional[Portfolio]:
        """Get the portfolio this item belongs to."""
        if not self.portfolio:
            self.portfolio = await Portfolio.get(self.portfolio_id)
        return self.portfolio

    model_config = {
        "validate_assignment": True,
        "json_encoders": {datetime: lambda v: v.isoformat()},
        "collection": "portfolio_items",
        "indexes": [
            "portfolio_id",
            "type",
            ("portfolio_id", "type"),
            ("portfolio_id", "is_featured"),
        ],
    }
