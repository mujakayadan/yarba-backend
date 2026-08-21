"""Immutable legal document versions and append-only acceptance evidence."""

from datetime import UTC, datetime
from enum import StrEnum

from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel

from core.models.document_config import BSON_DATETIME_ENCODERS, DOCUMENT_MODEL_CONFIG


class LegalDocumentType(StrEnum):
    """Legal documents published by Yarba."""

    TERMS = "terms"
    PRIVACY = "privacy"
    ACCEPTABLE_USE = "acceptable_use"
    COPYRIGHT_DMCA = "copyright_dmca"
    AI_DATA_USE = "ai_data_use"
    SITE_VISITOR_PRIVACY = "site_visitor_privacy"


class LegalDocumentVersion(Document):
    """An immutable, content-addressed legal document."""

    document_type: LegalDocumentType
    version: str
    title: str
    content: str
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    effective_at: datetime
    published_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    is_current: bool = True

    model_config = DOCUMENT_MODEL_CONFIG

    class Settings:
        name = "legal_document_versions"
        use_state_management = True
        indexes = [
            IndexModel(
                [("document_type", ASCENDING), ("version", ASCENDING)],
                unique=True,
            ),
            IndexModel([("document_type", ASCENDING), ("is_current", ASCENDING)]),
        ]
        bson_encoders = BSON_DATETIME_ENCODERS


class LegalAcceptance(Document):
    """Append-only evidence of a user's agreement, notice acknowledgement, or age claim."""

    user_id: PydanticObjectId
    document_type: LegalDocumentType
    document_version: str
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    accepted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    acceptance_kind: str
    source: str
    ip_address: str | None = None
    user_agent: str | None = None
    age_13_or_older: bool = True

    model_config = DOCUMENT_MODEL_CONFIG

    class Settings:
        name = "legal_acceptances"
        use_state_management = True
        indexes = [
            "user_id",
            IndexModel(
                [
                    ("user_id", ASCENDING),
                    ("document_type", ASCENDING),
                    ("document_version", ASCENDING),
                ],
                unique=True,
            ),
            IndexModel(
                [
                    ("user_id", ASCENDING),
                    ("document_type", ASCENDING),
                    ("accepted_at", DESCENDING),
                ]
            ),
        ]
        bson_encoders = BSON_DATETIME_ENCODERS
