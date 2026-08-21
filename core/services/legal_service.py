"""Version validation and append-only legal acceptance evidence."""

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from beanie import PydanticObjectId

from api.schemas.legal import LegalAcceptanceRequest, LegalAcceptanceStatus
from core.constants.legal_documents import APPROVED_LEGAL_DOCUMENTS, LEGAL_VERSION
from core.exceptions.base import ValidationException
from core.models.legal import LegalAcceptance, LegalDocumentType, LegalDocumentVersion
from core.repositories.legal_repository import (
    LegalAcceptanceRepository,
    LegalDocumentRepository,
)

_REQUIRED_TYPES = (
    LegalDocumentType.TERMS,
    LegalDocumentType.ACCEPTABLE_USE,
    LegalDocumentType.PRIVACY,
    LegalDocumentType.AI_DATA_USE,
)


@dataclass(frozen=True, slots=True)
class AcceptanceEvidence:
    ip_address: str | None = None
    user_agent: str | None = None


class LegalService:
    def __init__(
        self,
        documents: LegalDocumentRepository | None = None,
        acceptances: LegalAcceptanceRepository | None = None,
    ) -> None:
        self.documents = documents or LegalDocumentRepository()
        self.acceptances = acceptances or LegalAcceptanceRepository()

    async def current_documents(self) -> list[LegalDocumentVersion]:
        return await self.documents.current()

    async def ensure_documents_seeded(self) -> None:
        effective_at = datetime.strptime(LEGAL_VERSION, "%Y-%m-%d").replace(tzinfo=UTC)
        for document_type_value, (title, content) in APPROVED_LEGAL_DOCUMENTS.items():
            content_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
            await self.documents.replace_current(
                LegalDocumentVersion(
                    document_type=LegalDocumentType(document_type_value),
                    version=LEGAL_VERSION,
                    title=title,
                    content=content,
                    content_sha256=content_sha256,
                    effective_at=effective_at,
                )
            )

    async def history(
        self, document_type: LegalDocumentType | None = None
    ) -> list[LegalDocumentVersion]:
        return await self.documents.history(document_type)

    async def accept(
        self,
        user_id: PydanticObjectId,
        request: LegalAcceptanceRequest,
        evidence: AcceptanceEvidence | None = None,
    ) -> LegalAcceptanceStatus:
        current = await self.validate(request)
        metadata = evidence or AcceptanceEvidence()
        existing = {
            (record.document_type, record.document_version)
            for record in await self.acceptances.for_user(user_id)
        }
        records = [
            LegalAcceptance(
                user_id=user_id,
                document_type=kind,
                document_version=document.version,
                content_sha256=document.content_sha256,
                acceptance_kind=(
                    "agreement"
                    if kind
                    in {LegalDocumentType.TERMS, LegalDocumentType.ACCEPTABLE_USE}
                    else "acknowledgement"
                ),
                source=request.acceptance_surface,
                ip_address=metadata.ip_address,
                user_agent=metadata.user_agent,
                age_13_or_older=request.minimum_age_confirmed,
            )
            for kind, document in current.items()
            if (kind, document.version) not in existing
        ]
        await self.acceptances.append_many(records)
        return await self.status(user_id)

    async def validate(
        self, request: LegalAcceptanceRequest
    ) -> dict[LegalDocumentType, LegalDocumentVersion]:
        current = await self._required_current()
        submitted = {
            LegalDocumentType.TERMS: request.terms_version,
            LegalDocumentType.ACCEPTABLE_USE: request.acceptable_use_version,
            LegalDocumentType.PRIVACY: request.privacy_version,
            LegalDocumentType.AI_DATA_USE: request.ai_data_use_version,
        }
        if any(submitted[kind] != current[kind].version for kind in _REQUIRED_TYPES):
            raise ValidationException(
                "Legal documents have changed; review and accept the current versions"
            )
        return current

    async def validate_publication_acknowledgement(self, version: str) -> None:
        current = await self._required_current()
        acceptable_use = current[LegalDocumentType.ACCEPTABLE_USE]
        if version != acceptable_use.version:
            raise ValidationException(
                "The Acceptable Use Policy has changed; review it before publishing"
            )

    async def status(self, user_id: PydanticObjectId) -> LegalAcceptanceStatus:
        current = await self._required_current()
        evidence = await self.acceptances.for_user(user_id)
        accepted: dict[str, str] = {}
        for record in evidence:
            accepted.setdefault(record.document_type.value, record.document_version)
        current_versions = {
            kind.value: document.version for kind, document in current.items()
        }
        return LegalAcceptanceStatus(
            requires_acceptance=any(
                accepted.get(kind.value) != current[kind].version
                for kind in _REQUIRED_TYPES
            ),
            current_versions=current_versions,
            accepted_versions=accepted,
        )

    async def _required_current(
        self,
    ) -> dict[LegalDocumentType, LegalDocumentVersion]:
        current = {item.document_type: item for item in await self.documents.current()}
        if any(kind not in current for kind in _REQUIRED_TYPES):
            raise RuntimeError("Current legal documents are not seeded")
        return current
