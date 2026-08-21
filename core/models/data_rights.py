"""Account export and deletion request models."""

from datetime import UTC, datetime
from enum import StrEnum

from beanie import Document, PydanticObjectId
from pydantic import Field

from core.models.document_config import BSON_DATETIME_ENCODERS, DOCUMENT_MODEL_CONFIG


class ExportStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    EXPIRED = "expired"


class AccountExportRequest(Document):
    user_id: PydanticObjectId
    status: ExportStatus = ExportStatus.PENDING
    archive_key: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    expires_at: datetime | None = None
    error_message: str | None = None

    model_config = DOCUMENT_MODEL_CONFIG

    class Settings:
        name = "account_export_requests"
        use_state_management = True
        indexes = ["user_id", "status", "expires_at"]
        bson_encoders = BSON_DATETIME_ENCODERS


class DeletionStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AccountDeletionRequest(Document):
    user_id: PydanticObjectId
    status: DeletionStatus = DeletionStatus.PENDING
    requested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    scheduled_for: datetime
    was_active: bool = True
    cancelled_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = DOCUMENT_MODEL_CONFIG

    class Settings:
        name = "account_deletion_requests"
        use_state_management = True
        indexes = ["user_id", "status", "scheduled_for"]
        bson_encoders = BSON_DATETIME_ENCODERS
