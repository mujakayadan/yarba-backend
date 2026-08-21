"""Legal document and acceptance API schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from core.models.legal import LegalDocumentType


class LegalAcceptanceRequest(BaseModel):
    terms_version: str
    acceptable_use_version: str
    privacy_version: str
    ai_data_use_version: str
    terms_accepted: Literal[True]
    acceptable_use_accepted: Literal[True]
    privacy_acknowledged: Literal[True]
    ai_data_use_acknowledged: Literal[True]
    minimum_age_confirmed: Literal[True]
    acceptance_surface: Literal[
        "password_registration",
        "firebase_registration",
        "google_oauth",
        "apple_oauth",
        "settings_reacceptance",
    ]


class LegalDocumentResponse(BaseModel):
    document_type: LegalDocumentType
    version: str
    title: str
    content: str
    content_sha256: str
    effective_at: datetime


class LegalAcceptanceStatus(BaseModel):
    requires_acceptance: bool
    current_versions: dict[str, str]
    accepted_versions: dict[str, str]
