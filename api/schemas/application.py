"""API schemas for job application tracking."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from core.schemas.application_schemas import ApplicationProfile


class JobApplicationCreate(BaseModel):
    job_url: str | None = None
    company_name: str | None = None
    job_title: str | None = None
    resume_id: str | None = None
    cover_letter_id: str | None = None
    status: str = "draft"
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class JobApplicationUpdate(BaseModel):
    status: str
    error_message: str | None = None
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")


class JobApplicationResponse(BaseModel):
    id: str
    job_url: str | None
    company_name: str | None
    job_title: str | None
    platform: str | None
    resume_id: str | None
    cover_letter_id: str | None
    status: str
    submitted_at: datetime | None
    error_message: str | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(extra="forbid")


class PaginatedJobApplicationResponse(BaseModel):
    items: list[JobApplicationResponse]
    total: int

    model_config = ConfigDict(extra="forbid")


class ApplicationPrepareRequest(BaseModel):
    job_url: str | None = None
    job_description: str | None = None
    compile_pdf: bool = True
    generate_cover_letter: bool = False

    model_config = ConfigDict(extra="forbid")


class ApplicationPrepareResponse(BaseModel):
    application_id: str
    resume_id: str
    application_profile: ApplicationProfile

    model_config = ConfigDict(extra="forbid")
