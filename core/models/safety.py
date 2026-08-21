"""Abuse reporting and moderation audit persistence."""

from datetime import UTC, datetime, timedelta
from enum import StrEnum

from beanie import Document, PydanticObjectId
from pydantic import EmailStr, Field, HttpUrl
from pymongo import IndexModel

from core.models.document_config import BSON_DATETIME_ENCODERS, DOCUMENT_MODEL_CONFIG


class AbuseReportCategory(StrEnum):
    """Supported public report categories."""

    ILLEGAL_CONTENT = "illegal_content"
    SEXUAL_CONTENT = "sexual_content"
    MINOR_SAFETY = "minor_safety"
    NON_CONSENSUAL_INTIMATE_IMAGE = "non_consensual_intimate_image"
    COPYRIGHT = "copyright"
    HARASSMENT = "harassment"
    IMPERSONATION = "impersonation"
    PRIVACY = "privacy"
    MALWARE_OR_PHISHING = "malware_or_phishing"
    OTHER = "other"


class AbuseReportStatus(StrEnum):
    """Administrative report lifecycle."""

    OPEN = "open"
    UNDER_REVIEW = "under_review"
    ACTIONED = "actioned"
    REJECTED = "rejected"
    CLOSED = "closed"


class AbuseReport(Document):
    """A public abuse, NCII, or copyright report."""

    category: AbuseReportCategory
    status: AbuseReportStatus = AbuseReportStatus.OPEN
    reported_url: HttpUrl | None = None
    subdomain: str | None = None
    portfolio_website_id: PydanticObjectId | None = None
    reported_user_id: PydanticObjectId | None = None
    reporter_email: EmailStr | None = None
    description: str = Field(min_length=20, max_length=10_000)
    source_ip_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    copyright_owner: str | None = None
    copyrighted_work: str | None = None
    good_faith_statement: bool | None = None
    accuracy_statement: bool | None = None
    signature: str | None = None
    ncii_subject_is_reporter: bool | None = None
    ncii_consent_absent: bool | None = None
    due_at: datetime | None = None
    assigned_to: PydanticObjectId | None = None
    resolution_notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None
    retention_expires_at: datetime | None = None

    model_config = DOCUMENT_MODEL_CONFIG

    class Settings:
        name = "abuse_reports"
        use_state_management = True
        indexes = [
            "status",
            "category",
            "portfolio_website_id",
            "reported_user_id",
            "due_at",
            IndexModel([("retention_expires_at", 1)], expireAfterSeconds=0),
        ]
        bson_encoders = BSON_DATETIME_ENCODERS


class ModerationAuditEvent(Document):
    """Append-only record of an operator moderation decision."""

    actor_user_id: PydanticObjectId
    action: str
    target_type: str
    target_id: str
    report_id: PydanticObjectId | None = None
    reason: str
    metadata: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    retention_expires_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC) + timedelta(days=1095)
    )

    model_config = DOCUMENT_MODEL_CONFIG

    class Settings:
        name = "moderation_audit_events"
        use_state_management = True
        indexes = [
            "actor_user_id",
            "target_id",
            "report_id",
            "created_at",
            IndexModel([("retention_expires_at", 1)], expireAfterSeconds=0),
        ]
        bson_encoders = BSON_DATETIME_ENCODERS
