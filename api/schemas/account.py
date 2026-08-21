"""Account data export and deletion API schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from core.models.data_rights import DeletionStatus, ExportStatus


class AccountExportStatus(BaseModel):
    request_id: str | None = None
    status: ExportStatus | Literal["not_requested"]
    created_at: datetime | None = None
    completed_at: datetime | None = None
    expires_at: datetime | None = None
    download_url: str | None = None
    error_message: str | None = None


class AccountDeletionRequestBody(BaseModel):
    confirmation: Literal["DELETE"]
    current_password: str | None = Field(default=None, max_length=64)


class AccountDeletionStatus(BaseModel):
    request_id: str | None = None
    status: DeletionStatus | Literal["not_requested"]
    requested_at: datetime | None = None
    scheduled_for: datetime | None = None
    can_cancel: bool
