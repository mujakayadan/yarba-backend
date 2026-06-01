"""Portfolio models for the RBT database."""

from datetime import UTC, datetime
from typing import Any

from beanie import Document, Link, PydanticObjectId
from pydantic import BaseModel, Field, HttpUrl, model_validator

from core.models.profile import Profile
from core.models.user import User


class CareerSummary(BaseModel):
    """Career summary information including job titles and experience."""

    job_titles: list[str] = Field(
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
    responsibilities: list[str] = Field(default=[])

    model_config = {"validate_assignment": True}


class Education(BaseModel):
    """Education entry."""

    degree_type: str = Field(default="")
    degree: str = Field(default="")
    university_name: str = Field(default="")
    time: str = Field(default="")
    location: str = Field(default="")
    GPA: str = Field(default="")
    transcript: list[str] = Field(default=[])

    model_config = {"validate_assignment": True}


class Project(BaseModel):
    """Project entry."""

    name: str = Field(default="")
    bullet_points: list[str] = Field(default=[])
    date: str = Field(default="")
    link: HttpUrl | None = Field(
        default=None, description="Optional link to the project."
    )

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

    enabled: list[str] = Field(default=[])
    order: list[str] = Field(default=[])

    model_config = {"validate_assignment": True}


class Skill(BaseModel):
    """Skill category with a list of skills."""

    category: str = Field(default="")
    skills: list[str] = Field(default=[])

    model_config = {"validate_assignment": True}


class Portfolio(Document):
    """Portfolio model for storing professional information."""

    user_id: PydanticObjectId = Field(
        description="ID of the user who owns this portfolio."
    )
    profile_id: PydanticObjectId | None = Field(
        default=None, description="ID of the profile associated with this portfolio."
    )
    user: Link[User] | None = None
    profile: Link[Profile] | None = None

    career_summary: CareerSummary = Field(
        default_factory=CareerSummary,
        description="Career summary information, including multiple job titles and experience.",
    )

    skills: list[Skill] = Field(
        default_factory=list,
        description="List of skill categories and their skills.",
    )

    work_experience: list[WorkExperience] = Field(
        default=[], description="List of work experiences."
    )

    education: list[Education] = Field(
        default=[], description="List of education entries."
    )

    projects: list[Project] = Field(default=[], description="List of projects.")

    awards: list[Award] = Field(default=[], description="List of awards.")

    publications: list[Publication] = Field(
        default=[], description="List of publications."
    )

    certifications: list[Any] = Field(default=[], description="List of certifications.")

    custom_sections: CustomSections = Field(
        default_factory=CustomSections, description="Custom sections configuration."
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the portfolio was created.",
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the portfolio was last updated.",
    )

    class Settings:
        """Beanie document settings."""

        name = "portfolios"
        use_state_management = True
        indexes = ["user_id", "profile_id"]
        bson_encoders = {
            datetime: lambda dt: (dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt),
        }
