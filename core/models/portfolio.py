"""Portfolio models for the RBT database."""

import re
from datetime import UTC, datetime
from typing import Any

from beanie import Document, Link, PydanticObjectId
from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from core.models.document_config import BSON_DATETIME_ENCODERS, NESTED_MODEL_CONFIG
from core.models.profile import Profile
from core.models.user import User

MONTH_VALUE_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
DATE_RANGE_SEPARATOR_PATTERN = re.compile(r"\s+(?:-|–|—|to)\s+", re.IGNORECASE)
PRESENT_TERMS = ("present", "current", "now")


def _parse_month_value(value: str | None, *, range_end: bool = False) -> int:
    """Convert supported portfolio month text to a sortable YYYYMM integer."""
    if not value:
        return 0

    normalized = value.strip()
    if not normalized:
        return 0

    if any(term in normalized.lower() for term in PRESENT_TERMS):
        return 999_912

    formats = (
        "%Y-%m",
        "%m/%Y",
        "%m-%Y",
        "%m/%y",
        "%m-%y",
        "%b %Y",
        "%B %Y",
    )
    for date_format in formats:
        try:
            parsed = datetime.strptime(normalized, date_format)
            return parsed.year * 100 + parsed.month
        except ValueError:
            continue

    if re.fullmatch(r"\d{4}", normalized):
        return int(normalized) * 100 + (12 if range_end else 1)

    return 0


def _parse_time_range(value: str) -> tuple[int, int, bool]:
    """Return the start, end, and current status from a legacy time string."""
    if not value.strip():
        return 0, 0, False

    is_current = any(term in value.lower() for term in PRESENT_TERMS)
    parts = DATE_RANGE_SEPARATOR_PATTERN.split(value.strip(), maxsplit=1)
    start = _parse_month_value(parts[0])
    if is_current:
        return start, 999_912, True
    if len(parts) == 2:
        return start, _parse_month_value(parts[1], range_end=True), False

    parsed = _parse_month_value(value, range_end=True)
    return parsed, parsed, False


def _format_month_value(value: str) -> str:
    return datetime.strptime(value, "%Y-%m").strftime("%b %Y")


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

    model_config = NESTED_MODEL_CONFIG

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
    start_date: str | None = Field(
        default=None,
        description="Employment start month in YYYY-MM format.",
    )
    end_date: str | None = Field(
        default=None,
        description="Employment end month in YYYY-MM format.",
    )
    current: bool = Field(default=False)
    responsibilities: list[str] = Field(default=[])

    model_config = NESTED_MODEL_CONFIG

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def validate_month_value(cls, value: object) -> object:
        """Require structured employment dates to use HTML month input format."""
        if value in (None, ""):
            return None
        if not isinstance(value, str) or not MONTH_VALUE_PATTERN.fullmatch(value):
            raise ValueError("must use YYYY-MM format")
        return value

    @model_validator(mode="after")
    def validate_date_range(self) -> "WorkExperience":
        """Validate structured dates and keep the display period consistent."""
        has_structured_date = bool(self.start_date or self.end_date or self.current)
        if not has_structured_date:
            return self

        if not self.start_date:
            raise ValueError("start_date is required")
        if self.current and self.end_date:
            raise ValueError("end_date must be empty for a current job")
        if not self.current and not self.end_date:
            raise ValueError("end_date is required unless this is a current job")
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        current_month = datetime.now(UTC).strftime("%Y-%m")
        if self.start_date > current_month:
            raise ValueError("start_date must not be in the future")
        if self.end_date and self.end_date > current_month:
            raise ValueError("end_date must not be in the future")

        start_label = _format_month_value(self.start_date)
        end_label = (
            "Present" if self.current else _format_month_value(self.end_date or "")
        )
        object.__setattr__(self, "time", f"{start_label} - {end_label}")
        return self

    def date_sort_key(self) -> tuple[int, int, int]:
        """Return a deterministic newest-first sort key."""
        legacy_start, legacy_end, legacy_current = _parse_time_range(self.time)
        start = _parse_month_value(self.start_date) or legacy_start
        end = (
            999_912
            if self.current
            else _parse_month_value(self.end_date, range_end=True)
            or legacy_end
            or start
        )
        return int(self.current or legacy_current), end, start


def sort_work_experience(
    work_experience: list[WorkExperience],
) -> list[WorkExperience]:
    """Sort jobs from current/newest to oldest without mutating the input list."""
    return sorted(
        work_experience,
        key=WorkExperience.date_sort_key,
        reverse=True,
    )


class Education(BaseModel):
    """Education entry."""

    degree_type: str = Field(default="")
    degree: str = Field(default="")
    university_name: str = Field(default="")
    time: str = Field(default="")
    location: str = Field(default="")
    GPA: str = Field(default="")
    transcript: list[str] = Field(default=[])

    model_config = NESTED_MODEL_CONFIG


class Project(BaseModel):
    """Project entry."""

    name: str = Field(default="")
    bullet_points: list[str] = Field(default=[])
    date: str = Field(default="")
    link: HttpUrl | None = Field(
        default=None, description="Optional link to the project."
    )

    model_config = NESTED_MODEL_CONFIG


class Award(BaseModel):
    """Award entry."""

    name: str = Field(default="")
    explanation: str = Field(default="")

    model_config = NESTED_MODEL_CONFIG


class Publication(BaseModel):
    """Publication entry."""

    name: str = Field(default="")
    publisher: str = Field(default="")
    link: str = Field(default="")
    time: str = Field(default="")

    model_config = NESTED_MODEL_CONFIG


class CustomSections(BaseModel):
    """Custom sections configuration."""

    enabled: list[str] = Field(default=[])
    order: list[str] = Field(default=[])

    model_config = NESTED_MODEL_CONFIG


class Skill(BaseModel):
    """Skill category with a list of skills."""

    category: str = Field(default="")
    skills: list[str] = Field(default=[])

    model_config = NESTED_MODEL_CONFIG


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
        bson_encoders = BSON_DATETIME_ENCODERS

    @model_validator(mode="after")
    def sort_dated_sections(self) -> "Portfolio":
        """Keep work history in the canonical newest-to-oldest order."""
        self.work_experience = sort_work_experience(self.work_experience)
        return self
