"""Repositories for reports and moderation audit events."""

from core.models.safety import AbuseReport, ModerationAuditEvent
from core.repositories.base_repository import BeanieRepository


class AbuseReportRepository(BeanieRepository[AbuseReport]):
    def __init__(self) -> None:
        super().__init__(AbuseReport)


class ModerationAuditRepository(BeanieRepository[ModerationAuditEvent]):
    def __init__(self) -> None:
        super().__init__(ModerationAuditEvent)
