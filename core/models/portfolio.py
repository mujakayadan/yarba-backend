"""Portfolio models for the RBT database."""

from datetime import datetime, timezone
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
    default_job_title: str = Field(
        default="",
        description="Default job title to use when hardcoding or when LLM fails to select one.",
    )
    years_of_experience: str = Field(
        default="", description="Years of experience in the field."
    )
    default_summary: str = Field(
        default="",
        description="Default career summary to use when a custom one is not generated.",
    )

    model_config = {"validate_assignment": True}

    @model_validator(mode="after")
    def set_default_job_title_if_empty(self) -> "CareerSummary":
        """Set default_job_title to the first job title if not specified and job_titles exists."""
        if not self.default_job_title and self.job_titles:
            self.default_job_title = self.job_titles[0]
        return self


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

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the portfolio was created.",
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the portfolio was last updated.",
    )

    class Settings:
        """Beanie document settings."""

        name = "portfolios"
        use_state_management = True
        indexes = ["user_id", "profile_id"]
        bson_encoders = {
            datetime: lambda dt: (
                dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
            ),
        }
