"""Superuser abuse-report review and portfolio enforcement endpoints."""

from datetime import UTC, datetime, timedelta

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from api.middleware.auth import CurrentSuperuser
from api.schemas.safety import (
    AbuseReportAdminResponse,
    AbuseReportReviewRequest,
    PortfolioModerationRequest,
)
from core.models.safety import AbuseReport
from core.services.moderation_service import ModerationService
from core.utils.object_id import require_object_id

router = APIRouter(prefix="/admin/moderation", tags=["admin-moderation"])


def get_moderation_service() -> ModerationService:
    return ModerationService()


def _report_response(report: AbuseReport) -> AbuseReportAdminResponse:
    return AbuseReportAdminResponse(
        id=str(report.id),
        category=report.category,
        status=report.status,
        subdomain=report.subdomain,
        description=report.description,
        reporter_email=report.reporter_email,
        due_at=report.due_at,
        created_at=report.created_at,
    )


@router.get("/reports", response_model=list[AbuseReportAdminResponse])
async def list_reports(
    _current_user: CurrentSuperuser,
    report_status: str | None = None,
) -> list[AbuseReportAdminResponse]:
    query = {"status": report_status} if report_status else {}
    reports = await AbuseReport.find(query).sort("-created_at").to_list()
    return [_report_response(report) for report in reports]


@router.patch("/reports/{report_id}", response_model=AbuseReportAdminResponse)
async def review_report(
    report_id: str,
    body: AbuseReportReviewRequest,
    current_user: CurrentSuperuser,
) -> AbuseReportAdminResponse:
    try:
        report = await AbuseReport.get(PydanticObjectId(report_id))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    report.status = body.status
    report.resolution_notes = body.resolution_notes
    report.assigned_to = require_object_id(current_user.id)
    report.updated_at = datetime.now(UTC)
    if body.status.value in {"actioned", "rejected", "closed"}:
        report.resolved_at = report.updated_at
        report.retention_expires_at = report.updated_at + timedelta(days=1095)
    await report.save()
    return _report_response(report)


@router.post("/portfolio-websites/{website_id}/suspend")
async def suspend_website(
    website_id: str,
    body: PortfolioModerationRequest,
    current_user: CurrentSuperuser,
    service: ModerationService = Depends(get_moderation_service),
) -> dict[str, str]:
    website = await service.suspend(
        PydanticObjectId(website_id),
        require_object_id(current_user.id),
        body.reason,
    )
    return {"id": str(website.id), "moderation_status": website.moderation_status.value}


@router.post("/portfolio-websites/{website_id}/reinstate")
async def reinstate_website(
    website_id: str,
    body: PortfolioModerationRequest,
    current_user: CurrentSuperuser,
    service: ModerationService = Depends(get_moderation_service),
) -> dict[str, str]:
    website = await service.reinstate(
        PydanticObjectId(website_id),
        require_object_id(current_user.id),
        body.reason,
    )
    return {"id": str(website.id), "moderation_status": website.moderation_status.value}
