"""Public legal documents and authenticated acceptance endpoints."""

from fastapi import APIRouter, Depends, Request

from api.dependencies.auth import CurrentActiveUser
from api.schemas.legal import (
    LegalAcceptanceRequest,
    LegalAcceptanceStatus,
    LegalDocumentResponse,
)
from core.models.legal import LegalDocumentType
from core.services.legal_service import AcceptanceEvidence, LegalService
from core.utils.object_id import require_object_id

router = APIRouter(prefix="/legal", tags=["legal"])


def get_legal_service() -> LegalService:
    return LegalService()


@router.get("/documents/current", response_model=list[LegalDocumentResponse])
async def current_documents(
    service: LegalService = Depends(get_legal_service),
) -> list[LegalDocumentResponse]:
    return [
        LegalDocumentResponse.model_validate(document, from_attributes=True)
        for document in await service.current_documents()
    ]


@router.get("/documents/history", response_model=list[LegalDocumentResponse])
async def document_history(
    document_type: LegalDocumentType | None = None,
    service: LegalService = Depends(get_legal_service),
) -> list[LegalDocumentResponse]:
    return [
        LegalDocumentResponse.model_validate(document, from_attributes=True)
        for document in await service.history(document_type)
    ]


@router.get("/acceptances/me", response_model=LegalAcceptanceStatus)
async def acceptance_status(
    current_user: CurrentActiveUser,
    service: LegalService = Depends(get_legal_service),
) -> LegalAcceptanceStatus:
    return await service.status(require_object_id(current_user.id))


@router.post("/acceptances", response_model=LegalAcceptanceStatus)
async def accept_documents(
    body: LegalAcceptanceRequest,
    request: Request,
    current_user: CurrentActiveUser,
    service: LegalService = Depends(get_legal_service),
) -> LegalAcceptanceStatus:
    forwarded = request.headers.get("x-forwarded-for")
    ip_address = (
        forwarded.split(",", 1)[0].strip()
        if forwarded
        else (request.client.host if request.client else None)
    )
    return await service.accept(
        require_object_id(current_user.id),
        body,
        AcceptanceEvidence(
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent"),
        ),
    )
