"""Legal version validation and acceptance evidence tests."""

import hashlib
from datetime import UTC, datetime

import pytest
from beanie import PydanticObjectId

from api.schemas.legal import LegalAcceptanceRequest
from core.exceptions.base import ValidationException
from core.models.legal import LegalAcceptance, LegalDocumentType, LegalDocumentVersion
from core.services.legal_service import LegalService


def _document(document_type: LegalDocumentType) -> LegalDocumentVersion:
    content = f"Current {document_type.value}"
    return LegalDocumentVersion(
        document_type=document_type,
        version="2026-08-19",
        title=document_type.value,
        content=content,
        content_sha256=hashlib.sha256(content.encode()).hexdigest(),
        effective_at=datetime(2026, 8, 19, tzinfo=UTC),
    )


def _request(version: str = "2026-08-19") -> LegalAcceptanceRequest:
    return LegalAcceptanceRequest(
        terms_version=version,
        acceptable_use_version=version,
        privacy_version=version,
        ai_data_use_version=version,
        terms_accepted=True,
        acceptable_use_accepted=True,
        privacy_acknowledged=True,
        ai_data_use_acknowledged=True,
        minimum_age_confirmed=True,
        acceptance_surface="settings_reacceptance",
    )


class FakeDocuments:
    def __init__(self) -> None:
        self.items = [
            _document(LegalDocumentType.TERMS),
            _document(LegalDocumentType.ACCEPTABLE_USE),
            _document(LegalDocumentType.PRIVACY),
            _document(LegalDocumentType.AI_DATA_USE),
        ]

    async def current(self) -> list[LegalDocumentVersion]:
        return self.items

    async def history(
        self, document_type: LegalDocumentType | None = None
    ) -> list[LegalDocumentVersion]:
        return [
            item
            for item in self.items
            if document_type is None or item.document_type == document_type
        ]


class FakeAcceptances:
    def __init__(self) -> None:
        self.items: list[LegalAcceptance] = []

    async def for_user(self, user_id: PydanticObjectId) -> list[LegalAcceptance]:
        return [item for item in self.items if item.user_id == user_id]

    async def append_many(self, records: list[LegalAcceptance]) -> None:
        self.items.extend(records)


@pytest.mark.asyncio
async def test_acceptance_is_versioned_and_idempotent(beanie_db: object) -> None:
    documents = FakeDocuments()
    acceptances = FakeAcceptances()
    service = LegalService(documents=documents, acceptances=acceptances)  # type: ignore[arg-type]
    user_id = PydanticObjectId()

    first = await service.accept(user_id, _request())
    second = await service.accept(user_id, _request())

    assert first.requires_acceptance is False
    assert second.requires_acceptance is False
    assert len(acceptances.items) == 4
    assert {item.document_type for item in acceptances.items} == {
        LegalDocumentType.TERMS,
        LegalDocumentType.ACCEPTABLE_USE,
        LegalDocumentType.PRIVACY,
        LegalDocumentType.AI_DATA_USE,
    }


@pytest.mark.asyncio
async def test_stale_legal_version_is_rejected(beanie_db: object) -> None:
    service = LegalService(  # type: ignore[arg-type]
        documents=FakeDocuments(),
        acceptances=FakeAcceptances(),
    )

    with pytest.raises(ValidationException):
        await service.validate(_request("2026-08-18"))
