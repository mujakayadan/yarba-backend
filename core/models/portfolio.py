"""Portfolio and PortfolioItem models for the RBT database."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from beanie import Document, Link, PydanticObjectId
from pydantic import BaseModel, Field, model_validator

from core.models.profile import Profile
from core.models.user import User


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


class Skill(BaseModel):
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

    skills: List[Skill] = Field(
        default_factory=list,
        description="List of skill categories and their skills.",
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
