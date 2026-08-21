"""Public abuse-report and administrative moderation schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from core.models.safety import AbuseReportCategory, AbuseReportStatus


class AbuseReportRequest(BaseModel):
    subdomain: str = Field(min_length=3, max_length=63, pattern=r"^[a-z0-9-]+$")
    reported_url: str | None = None
    category: AbuseReportCategory
    description: str = Field(min_length=20, max_length=10_000)
    reporter_email: EmailStr | None = None
    company_website: str | None = None


class AbuseReportResponse(BaseModel):
    report_id: str
    status: Literal["received"] = "received"
    message: str
    response_due_at: datetime | None = None


class AbuseReportReviewRequest(BaseModel):
    status: AbuseReportStatus
    resolution_notes: str = Field(min_length=3, max_length=10_000)


class PortfolioModerationRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2_000)


class AbuseReportAdminResponse(BaseModel):
    id: str
    category: AbuseReportCategory
    status: AbuseReportStatus
    subdomain: str | None
    description: str
    reporter_email: EmailStr | None
    due_at: datetime | None
    created_at: datetime
