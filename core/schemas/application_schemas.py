"""Schemas for job-application autofill payloads."""

from pydantic import BaseModel, ConfigDict

from core.schemas.application_preferences import Demographics, WorkEligibility
from core.schemas.application_preferences import LogisticsPreferences as LogisticsPrefs
from core.schemas.resume_schemas import (
    CareerSummarySchema,
    EducationSchema,
    ProjectSchema,
    SkillCategorySchema,
    WorkExperienceSchema,
)


class ApplicationContact(BaseModel):
    """Factual contact PII sourced ONLY from Profile.personal_information."""

    full_name: str | None = None
    email: str
    phone: str | None = None
    address: str | None = None
    linkedin: str | None = None
    github: str | None = None
    website: str | None = None

    model_config = ConfigDict(extra="forbid")


class ApplicationProfile(BaseModel):
    """Aggregated payload an apply client uses to fill a job form."""

    contact: ApplicationContact
    career_summary: CareerSummarySchema | None = None
    work_experience: list[WorkExperienceSchema] = []
    education: list[EducationSchema] = []
    skills: list[SkillCategorySchema] = []
    projects: list[ProjectSchema] = []
    cover_letter_text: str | None = None
    resume_id: str
    resume_pdf_download_path: str
    job_url: str | None = None
    job_title: str | None = None
    company_name: str | None = None
    work_eligibility: WorkEligibility | None = None
    logistics: LogisticsPrefs | None = None
    demographics: Demographics | None = None
    apply_account_password: str | None = None

    model_config = ConfigDict(extra="forbid")
