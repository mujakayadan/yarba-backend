"""Repositories for legal documents and acceptance evidence."""

from beanie import PydanticObjectId

from core.models.legal import LegalAcceptance, LegalDocumentType, LegalDocumentVersion
from core.repositories.base_repository import BeanieRepository


class LegalDocumentRepository(BeanieRepository[LegalDocumentVersion]):
    def __init__(self) -> None:
        super().__init__(LegalDocumentVersion)

    async def current(self) -> list[LegalDocumentVersion]:
        return (
            await LegalDocumentVersion.find({"is_current": True})
            .sort("document_type")
            .to_list()
        )

    async def history(
        self, document_type: LegalDocumentType | None = None
    ) -> list[LegalDocumentVersion]:
        query = {"document_type": document_type} if document_type else {}
        return await LegalDocumentVersion.find(query).sort("-effective_at").to_list()

    async def get_version(
        self, document_type: LegalDocumentType, version: str
    ) -> LegalDocumentVersion | None:
        return await LegalDocumentVersion.find_one(
            {"document_type": document_type, "version": version}
        )

    async def replace_current(self, document: LegalDocumentVersion) -> None:
        await LegalDocumentVersion.find(
            {
                "document_type": document.document_type,
                "is_current": True,
                "version": {"$ne": document.version},
            }
        ).update_many({"$set": {"is_current": False}})
        existing = await self.get_version(document.document_type, document.version)
        if existing is None:
            await self.create(document)
            return
        if existing.content_sha256 != document.content_sha256:
            raise RuntimeError(
                f"Legal document {document.document_type.value} "
                f"version {document.version} has changed"
            )
        if not existing.is_current:
            existing.is_current = True
            await existing.save()


class LegalAcceptanceRepository(BeanieRepository[LegalAcceptance]):
    def __init__(self) -> None:
        super().__init__(LegalAcceptance)

    async def for_user(self, user_id: PydanticObjectId) -> list[LegalAcceptance]:
        return (
            await LegalAcceptance.find({"user_id": user_id})
            .sort("-accepted_at")
            .to_list()
        )

    async def append_many(self, records: list[LegalAcceptance]) -> None:
        if records:
            await LegalAcceptance.insert_many(records)
