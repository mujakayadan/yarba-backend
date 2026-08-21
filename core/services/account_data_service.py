"""Account export, deletion scheduling, and retention enforcement."""

import json
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

import jwt
from beanie import Document, PydanticObjectId
from jwt.exceptions import PyJWTError

from config.settings import settings
from core.auth.firebase import FirebaseAuth
from core.auth.password import verify_password
from core.exceptions.base import (
    ConflictException,
    NotFoundException,
    UnauthorizedException,
)
from core.models.agent_access_token import AgentAccessToken
from core.models.auth_action_token import AuthActionToken
from core.models.auth_identity import AuthIdentity
from core.models.cover_letter import CoverLetter
from core.models.data_rights import (
    AccountDeletionRequest,
    AccountExportRequest,
    DeletionStatus,
    ExportStatus,
)
from core.models.inbound_email import InboundEmail
from core.models.job_application import JobApplication
from core.models.legal import LegalAcceptance
from core.models.portfolio import Portfolio
from core.models.portfolio_chat_conversation import PortfolioChatConversation
from core.models.portfolio_site_token import PortfolioSiteToken
from core.models.portfolio_website import PortfolioWebsite
from core.models.profile import Profile
from core.models.refresh_token_session import RefreshTokenSession
from core.models.resume import Resume
from core.models.unknown_email_sender import UnknownEmailSender
from core.models.user import User
from core.services.aws_deployment_service import AWSDeploymentService
from core.utils.field_encryption import decrypt_json
from utils.storage import StorageProvider, get_storage_provider

EXPORT_RETENTION_DAYS = 7
DELETION_GRACE_DAYS = 7


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class AccountDataService:
    """Create portable exports and execute cancellable account deletion."""

    def __init__(self, storage: StorageProvider | None = None) -> None:
        self.storage = storage or get_storage_provider()

    async def latest_export(
        self, user_id: PydanticObjectId
    ) -> AccountExportRequest | None:
        return await AccountExportRequest.find_one(
            {"user_id": user_id}, sort=[("created_at", -1)]
        )

    async def request_export(self, user: User) -> AccountExportRequest:
        user_id = self._user_id(user)
        latest = await self.latest_export(user_id)
        now = datetime.now(UTC)
        if latest is not None and latest.status in {
            ExportStatus.PENDING,
            ExportStatus.PROCESSING,
        }:
            return latest
        if (
            latest is not None
            and latest.status == ExportStatus.READY
            and latest.expires_at is not None
            and _as_utc(latest.expires_at) > now
        ):
            return latest

        export = AccountExportRequest(user_id=user_id, status=ExportStatus.PROCESSING)
        await export.insert()
        try:
            archive = await self._build_archive(user)
            export.archive_key = await self.storage.save_account_export(
                archive, str(export.id)
            )
            export.status = ExportStatus.READY
            export.completed_at = now
            export.expires_at = now + timedelta(days=EXPORT_RETENTION_DAYS)
        except Exception as exc:
            export.status = ExportStatus.FAILED
            export.error_message = str(exc)[:500]
            await export.save()
            raise
        await export.save()
        return export

    def download_url(
        self, export: AccountExportRequest, api_base_url: str
    ) -> str | None:
        if (
            export.id is None
            or export.status != ExportStatus.READY
            or export.expires_at is None
            or _as_utc(export.expires_at) <= datetime.now(UTC)
        ):
            return None
        token = jwt.encode(
            {
                "sub": str(export.user_id),
                "export_id": str(export.id),
                "purpose": "account_export",
                "exp": _as_utc(export.expires_at),
            },
            settings.auth.jwt_secret_key.get_secret_value(),
            algorithm=settings.auth.jwt_algorithm,
        )
        base = api_base_url.rstrip("/")
        return f"{base}/account/exports/{export.id}/download?token={token}"

    async def get_download(self, export_id: str, token: str) -> tuple[bytes, str]:
        try:
            payload = jwt.decode(
                token,
                settings.auth.jwt_secret_key.get_secret_value(),
                algorithms=[settings.auth.jwt_algorithm],
            )
        except PyJWTError as exc:
            raise UnauthorizedException("Invalid or expired export link") from exc
        if (
            payload.get("purpose") != "account_export"
            or payload.get("export_id") != export_id
        ):
            raise UnauthorizedException("Invalid export link")
        try:
            export = await AccountExportRequest.get(PydanticObjectId(export_id))
        except Exception as exc:
            raise NotFoundException("Export not found") from exc
        if (
            export is None
            or str(export.user_id) != payload.get("sub")
            or export.status != ExportStatus.READY
            or export.archive_key is None
            or export.expires_at is None
            or _as_utc(export.expires_at) <= datetime.now(UTC)
        ):
            raise NotFoundException("Export is no longer available")
        return await self.storage.get_file(
            export.archive_key
        ), f"yarba-export-{export_id}.zip"

    async def deletion_status(
        self, user_id: PydanticObjectId
    ) -> AccountDeletionRequest | None:
        return await AccountDeletionRequest.find_one(
            {"user_id": user_id}, sort=[("requested_at", -1)]
        )

    async def request_deletion(
        self, user: User, current_password: str | None
    ) -> AccountDeletionRequest:
        user_id = self._user_id(user)
        existing = await self.deletion_status(user_id)
        if existing is not None and existing.status in {
            DeletionStatus.PENDING,
            DeletionStatus.PROCESSING,
        }:
            return existing
        if user.password_hash and (
            current_password is None
            or not verify_password(current_password, user.password_hash)
        ):
            raise UnauthorizedException("Current password is incorrect")

        now = datetime.now(UTC)
        deletion = AccountDeletionRequest(
            user_id=user_id,
            requested_at=now,
            scheduled_for=now + timedelta(days=DELETION_GRACE_DAYS),
            was_active=user.is_active,
        )
        await deletion.insert()
        user.is_active = False
        user.updated_at = now
        await user.save()
        await self._revoke_access(user_id, now)
        return deletion

    async def cancel_deletion(self, user: User) -> AccountDeletionRequest:
        user_id = self._user_id(user)
        deletion = await self.deletion_status(user_id)
        if deletion is None or deletion.status != DeletionStatus.PENDING:
            raise ConflictException("There is no cancellable deletion request")
        deletion.status = DeletionStatus.CANCELLED
        deletion.cancelled_at = datetime.now(UTC)
        await deletion.save()
        if deletion.was_active:
            user.is_active = True
            user.updated_at = deletion.cancelled_at
            await user.save()
        return deletion

    async def process_due_deletions(self) -> int:
        due = await AccountDeletionRequest.find(
            {
                "status": DeletionStatus.PENDING,
                "scheduled_for": {"$lte": datetime.now(UTC)},
            }
        ).to_list()
        for deletion in due:
            await self._execute_deletion(deletion)
        return len(due)

    async def purge_expired_exports(self) -> int:
        expired = await AccountExportRequest.find(
            {
                "status": ExportStatus.READY,
                "expires_at": {"$lte": datetime.now(UTC)},
            }
        ).to_list()
        for export in expired:
            if export.archive_key:
                await self.storage.delete_file(export.archive_key)
            export.status = ExportStatus.EXPIRED
            export.archive_key = None
            await export.save()
        return len(expired)

    async def _build_archive(self, user: User) -> bytes:
        user_id = self._user_id(user)
        profile = await Profile.find_one({"user_id": user_id})
        user_data = user.model_dump(
            mode="json", exclude={"password_hash", "linkedin_auth_token"}
        )
        profile_data: dict[str, Any] | None = None
        if profile is not None:
            profile_data = profile.model_dump(
                mode="json",
                exclude={
                    "api_keys",
                    "apply_credentials_encrypted",
                    "demographics_encrypted",
                },
            )
            if profile.demographics_encrypted:
                profile_data["demographics"] = decrypt_json(
                    profile.demographics_encrypted
                )

        payloads: dict[str, Any] = {
            "account": user_data,
            "profile": profile_data,
            "portfolio": await self._documents(Portfolio, user_id),
            "resumes": await self._documents(Resume, user_id),
            "cover_letters": await self._documents(CoverLetter, user_id),
            "applications": await self._documents(JobApplication, user_id),
            "portfolio_websites": await self._documents(PortfolioWebsite, user_id),
            "portfolio_chats": await self._documents(
                PortfolioChatConversation, user_id
            ),
            "legal_acceptances": await self._documents(LegalAcceptance, user_id),
        }
        output = BytesIO()
        with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
            for name, payload in payloads.items():
                archive.writestr(
                    f"{name}.json",
                    json.dumps(payload, indent=2, ensure_ascii=False),
                )
        return output.getvalue()

    async def _documents(
        self, model: type[Document], user_id: PydanticObjectId
    ) -> list[dict[str, Any]]:
        documents = await model.find({"user_id": user_id}).to_list()
        return [document.model_dump(mode="json") for document in documents]

    async def _execute_deletion(self, deletion: AccountDeletionRequest) -> None:
        deletion.status = DeletionStatus.PROCESSING
        await deletion.save()
        user_id = deletion.user_id
        user = await User.get(user_id)
        profile = await Profile.find_one({"user_id": user_id})
        website = await PortfolioWebsite.find_one({"user_id": user_id})
        resumes = await Resume.find({"user_id": user_id}).to_list()
        cover_letters = await CoverLetter.find({"user_id": user_id}).to_list()
        exports = await AccountExportRequest.find({"user_id": user_id}).to_list()

        object_keys = [
            *(
                [profile.profile_picture_key, profile.signature_key]
                if profile is not None
                else []
            ),
            *(resume.resume_pdf_key for resume in resumes),
            *(letter.cover_letter_pdf_key for letter in cover_letters),
            *(export.archive_key for export in exports),
        ]
        for object_key in object_keys:
            if object_key:
                await self.storage.delete_file(object_key)
        if website is not None and settings.storage.aws_bucket:
            await AWSDeploymentService().delete_website(website.subdomain)
        if user is not None and user.firebase_uid:
            await FirebaseAuth.delete_user(user.firebase_uid)

        for model in (
            AuthActionToken,
            AuthIdentity,
            RefreshTokenSession,
            AgentAccessToken,
            PortfolioSiteToken,
            PortfolioChatConversation,
            PortfolioWebsite,
            JobApplication,
            CoverLetter,
            Resume,
            Portfolio,
            Profile,
            AccountExportRequest,
        ):
            await model.find({"user_id": user_id}).delete()
        if user is not None:
            await InboundEmail.find({"sender_email": user.email}).delete()
            await UnknownEmailSender.find({"sender_email": user.email}).delete()
            await user.delete()
        await LegalAcceptance.find({"user_id": user_id}).update_many(
            {"$set": {"ip_address": None, "user_agent": None}}
        )
        deletion.status = DeletionStatus.COMPLETED
        deletion.completed_at = datetime.now(UTC)
        await deletion.save()

    async def _revoke_access(
        self, user_id: PydanticObjectId, revoked_at: datetime
    ) -> None:
        await RefreshTokenSession.find({"user_id": user_id}).update_many(
            {
                "$set": {
                    "revoked_at": revoked_at,
                    "revocation_reason": "account_deletion_requested",
                }
            }
        )
        await AgentAccessToken.find({"user_id": user_id}).update_many(
            {"$set": {"is_active": False, "updated_at": revoked_at}}
        )
        await PortfolioSiteToken.find({"user_id": user_id}).update_many(
            {"$set": {"is_active": False, "updated_at": revoked_at}}
        )

    def _user_id(self, user: User) -> PydanticObjectId:
        if user.id is None:
            raise ValueError("Persisted user is missing an id")
        return PydanticObjectId(user.id)
