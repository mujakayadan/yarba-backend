"""Abuse report intake and enforceable portfolio moderation."""

import hashlib
from datetime import UTC, datetime, timedelta

from beanie import PydanticObjectId

from api.schemas.safety import AbuseReportRequest, AbuseReportResponse
from config.settings import settings
from core.exceptions.base import NotFoundException
from core.models.portfolio_website import ModerationStatus, PortfolioWebsite
from core.models.safety import AbuseReport, AbuseReportCategory, ModerationAuditEvent
from core.repositories.portfolio_website_repository import PortfolioWebsiteRepository
from core.repositories.safety_repository import (
    AbuseReportRepository,
    ModerationAuditRepository,
)
from core.services.aws_deployment_service import AWSDeploymentService
from core.utils.object_id import require_object_id


class ModerationService:
    def __init__(
        self,
        reports: AbuseReportRepository | None = None,
        audits: ModerationAuditRepository | None = None,
        websites: PortfolioWebsiteRepository | None = None,
        aws: AWSDeploymentService | None = None,
    ) -> None:
        self.reports = reports or AbuseReportRepository()
        self.audits = audits or ModerationAuditRepository()
        self.websites = websites or PortfolioWebsiteRepository()
        self.aws = aws

    async def submit_report(
        self, body: AbuseReportRequest, client_ip: str
    ) -> AbuseReportResponse:
        if body.company_website:
            return AbuseReportResponse(
                report_id="received",
                message="Thank you. Your report was received.",
            )
        website = await self.websites.get_by_subdomain(body.subdomain)
        now = datetime.now(UTC)
        due_at = (
            now + timedelta(hours=48)
            if body.category
            in {
                AbuseReportCategory.MINOR_SAFETY,
                AbuseReportCategory.NON_CONSENSUAL_INTIMATE_IMAGE,
            }
            else None
        )
        secret = settings.auth.jwt_secret_key.get_secret_value()
        report = await self.reports.create(
            AbuseReport(
                category=body.category,
                subdomain=body.subdomain,
                reported_url=body.reported_url,
                portfolio_website_id=(
                    require_object_id(website.id) if website and website.id else None
                ),
                reported_user_id=website.user_id if website else None,
                reporter_email=body.reporter_email,
                description=body.description,
                source_ip_hash=hashlib.sha256(
                    f"{secret}:{client_ip}".encode()
                ).hexdigest(),
                due_at=due_at,
            )
        )
        return AbuseReportResponse(
            report_id=str(report.id),
            message="Thank you. Your report was received.",
            response_due_at=due_at,
        )

    async def suspend(
        self,
        website_id: PydanticObjectId,
        actor_id: PydanticObjectId,
        reason: str,
    ) -> PortfolioWebsite:
        website = await self.websites.get_by_id(website_id)
        if website is None:
            raise NotFoundException("Portfolio website not found")
        website.moderation_status = ModerationStatus.SUSPENDED
        website.moderation_message = (
            "This site is unavailable following a safety review."
        )
        website.suspension_reason = reason
        website.suspended_at = datetime.now(UTC)
        website.is_published = False
        website.is_indexable = False
        website.clean_redeploy_required = True
        await website.save()
        aws = self.aws or AWSDeploymentService()
        await aws.deploy_suspension_page(website.subdomain)
        await self._audit(actor_id, "suspend", website, reason)
        return website

    async def reinstate(
        self,
        website_id: PydanticObjectId,
        actor_id: PydanticObjectId,
        reason: str,
    ) -> PortfolioWebsite:
        website = await self.websites.get_by_id(website_id)
        if website is None:
            raise NotFoundException("Portfolio website not found")
        website.moderation_status = ModerationStatus.ACTIVE
        website.moderation_message = None
        website.suspension_reason = None
        website.suspended_at = None
        website.is_indexable = True
        website.clean_redeploy_required = True
        website.last_build_hash = None
        await website.save()
        await self._audit(actor_id, "reinstate", website, reason)
        return website

    async def _audit(
        self,
        actor_id: PydanticObjectId,
        action: str,
        website: PortfolioWebsite,
        reason: str,
    ) -> None:
        await self.audits.create(
            ModerationAuditEvent(
                actor_user_id=actor_id,
                action=action,
                target_type="portfolio_website",
                target_id=str(website.id),
                reason=reason,
            )
        )
