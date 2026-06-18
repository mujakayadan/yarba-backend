"""Job application tracking model."""

from datetime import UTC, datetime
from typing import Any

from beanie import Document, PydanticObjectId
from pydantic import Field

from core.models.document_config import BSON_DATETIME_ENCODERS

APPLICATION_STATUSES = frozenset(
    {"draft", "preview_ready", "submitted", "failed", "skipped"}
)


class JobApplication(Document):
    """Audit log for a job application attempt."""

    user_id: PydanticObjectId
    job_url: str | None = None
    company_name: str | None = None
    job_title: str | None = None
    platform: str | None = None
    resume_id: PydanticObjectId | None = None
    cover_letter_id: PydanticObjectId | None = None
    status: str = Field(default="draft")
    submitted_at: datetime | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "job_applications"
        indexes = ["user_id", "status"]
        bson_encoders = BSON_DATETIME_ENCODERS
