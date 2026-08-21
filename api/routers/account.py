"""Authenticated account export and deletion endpoints."""

from fastapi import APIRouter, Depends, Request, Response

from api.dependencies.auth import CurrentUser
from api.schemas.account import (
    AccountDeletionRequestBody,
    AccountDeletionStatus,
    AccountExportStatus,
)
from core.models.data_rights import (
    AccountDeletionRequest,
    AccountExportRequest,
    DeletionStatus,
    ExportStatus,
)
from core.services.account_data_service import AccountDataService
from core.utils.object_id import require_object_id

router = APIRouter(prefix="/account", tags=["account"])


def get_account_data_service() -> AccountDataService:
    return AccountDataService()


def _api_base_url(request: Request) -> str:
    return f"{str(request.base_url).rstrip('/')}/api/v1"


def _export_status(
    export: AccountExportRequest | None,
    service: AccountDataService,
    request: Request,
) -> AccountExportStatus:
    if export is None:
        return AccountExportStatus(status="not_requested")
    status = export.status
    download_url = service.download_url(export, _api_base_url(request))
    if status == ExportStatus.READY and download_url is None:
        status = ExportStatus.EXPIRED
    return AccountExportStatus(
        request_id=str(export.id),
        status=status,
        created_at=export.created_at,
        completed_at=export.completed_at,
        expires_at=export.expires_at,
        download_url=download_url,
        error_message=export.error_message,
    )


def _deletion_status(
    deletion: AccountDeletionRequest | None,
) -> AccountDeletionStatus:
    if deletion is None:
        return AccountDeletionStatus(status="not_requested", can_cancel=False)
    return AccountDeletionStatus(
        request_id=str(deletion.id),
        status=deletion.status,
        requested_at=deletion.requested_at,
        scheduled_for=deletion.scheduled_for,
        can_cancel=deletion.status == DeletionStatus.PENDING,
    )


@router.get("/exports/latest", response_model=AccountExportStatus)
async def latest_account_export(
    request: Request,
    current_user: CurrentUser,
    service: AccountDataService = Depends(get_account_data_service),
) -> AccountExportStatus:
    export = await service.latest_export(require_object_id(current_user.id))
    return _export_status(export, service, request)


@router.post("/exports", response_model=AccountExportStatus)
async def request_account_export(
    request: Request,
    current_user: CurrentUser,
    service: AccountDataService = Depends(get_account_data_service),
) -> AccountExportStatus:
    export = await service.request_export(current_user)
    return _export_status(export, service, request)


@router.get("/exports/{export_id}/download", name="download_account_export")
async def download_account_export(
    export_id: str,
    token: str,
    service: AccountDataService = Depends(get_account_data_service),
) -> Response:
    archive, filename = await service.get_download(export_id, token)
    return Response(
        content=archive,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/deletion", response_model=AccountDeletionStatus)
async def get_account_deletion(
    current_user: CurrentUser,
    service: AccountDataService = Depends(get_account_data_service),
) -> AccountDeletionStatus:
    deletion = await service.deletion_status(require_object_id(current_user.id))
    return _deletion_status(deletion)


@router.post("/deletion", response_model=AccountDeletionStatus)
async def request_account_deletion(
    body: AccountDeletionRequestBody,
    current_user: CurrentUser,
    service: AccountDataService = Depends(get_account_data_service),
) -> AccountDeletionStatus:
    deletion = await service.request_deletion(current_user, body.current_password)
    return _deletion_status(deletion)


@router.delete("/deletion", response_model=AccountDeletionStatus)
async def cancel_account_deletion(
    current_user: CurrentUser,
    service: AccountDataService = Depends(get_account_data_service),
) -> AccountDeletionStatus:
    deletion = await service.cancel_deletion(current_user)
    return _deletion_status(deletion)
