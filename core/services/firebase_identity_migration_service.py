"""Safe, idempotent reconciliation of Firebase users into native identities."""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from pydantic import EmailStr
from pymongo.errors import DuplicateKeyError

from core.auth.types import AuthMigrationState, IdentityProvider
from core.models.auth_identity import AuthIdentity
from core.models.user import User
from core.repositories.auth_identity_repository import AuthIdentityRepository
from core.repositories.user_repository import UserRepository
from core.utils.object_id import require_object_id


class FirebaseProviderRecord(Protocol):
    """Provider identity fields consumed from Firebase Admin records."""

    provider_id: str
    uid: str


@dataclass(frozen=True, slots=True)
class FirebaseUserRecord:
    """Credential-free Firebase user snapshot used by reconciliation."""

    uid: str
    email: str | None
    email_verified: bool
    has_password_credential: bool
    provider_data: tuple[FirebaseProviderRecord, ...] = ()


class MigrationDisposition(StrEnum):
    """Operator-facing reconciliation result."""

    READY = "ready"
    APPLIED = "applied"
    UNCHANGED = "unchanged"
    CONFLICT = "conflict"
    MISSING_MONGO_USER = "missing_mongo_user"
    MISSING_FIREBASE_RECORD = "missing_firebase_record"


class ResetEmailStatus(StrEnum):
    """Password reset campaign result."""

    NOT_REQUESTED = "not_requested"
    SENT = "sent"
    FAILED = "failed"


@dataclass(slots=True)
class MigrationAuditEntry:
    """Sensitive-but-token-free per-user audit result."""

    disposition: MigrationDisposition
    firebase_uid: str | None
    mongo_user_id: str | None
    email: str | None
    actions: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    password_reset_required: bool = False
    password_only_firebase_user: bool = False
    reset_email_status: ResetEmailStatus = ResetEmailStatus.NOT_REQUESTED
    reset_email_error: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialize only operator-safe audit fields."""
        return {
            "disposition": self.disposition.value,
            "firebase_uid": self.firebase_uid,
            "mongo_user_id": self.mongo_user_id,
            "email": self.email,
            "actions": self.actions,
            "conflicts": self.conflicts,
            "password_reset_required": self.password_reset_required,
            "password_only_firebase_user": self.password_only_firebase_user,
            "reset_email_status": self.reset_email_status.value,
            "reset_email_error": self.reset_email_error,
        }


@dataclass(slots=True)
class MigrationAuditReport:
    """Machine-readable migration report and process outcome."""

    mode: str
    generated_at: datetime
    entries: list[MigrationAuditEntry]
    apply_requested: bool = False
    allow_missing_records: bool = False
    apply_blocked: bool = False
    apply_blocked_reasons: list[str] = field(default_factory=list)

    @property
    def conflict_count(self) -> int:
        return sum(bool(entry.conflicts) for entry in self.entries)

    @property
    def reset_failure_count(self) -> int:
        return sum(
            entry.reset_email_status is ResetEmailStatus.FAILED
            for entry in self.entries
        )

    @property
    def review_required_count(self) -> int:
        return sum(
            entry.disposition
            in {
                MigrationDisposition.MISSING_MONGO_USER,
                MigrationDisposition.MISSING_FIREBASE_RECORD,
            }
            for entry in self.entries
        )

    @property
    def execution_status(self) -> str:
        if not self.apply_requested:
            return "dry_run_review_required" if self.has_failures else "dry_run_clean"
        if self.apply_blocked:
            return "apply_blocked"
        if self.conflict_count or self.reset_failure_count:
            return "applied_with_failures"
        return "applied"

    @property
    def has_failures(self) -> bool:
        missing_unaccepted = (
            self.review_required_count > 0 and not self.allow_missing_records
        )
        return (
            self.conflict_count > 0
            or self.reset_failure_count > 0
            or self.apply_blocked
            or missing_unaccepted
        )

    def to_dict(self) -> dict[str, object]:
        counts = Counter(entry.disposition.value for entry in self.entries)
        reset_candidates = [
            {
                "mongo_user_id": entry.mongo_user_id,
                "email": entry.email,
                "reset_email_status": entry.reset_email_status.value,
            }
            for entry in self.entries
            if entry.password_reset_required
        ]
        password_only_users = [
            {
                "mongo_user_id": entry.mongo_user_id,
                "email": entry.email,
                "reset_email_status": entry.reset_email_status.value,
            }
            for entry in self.entries
            if entry.password_only_firebase_user
        ]
        return {
            "sensitivity": (
                "Contains user identifiers and email addresses; restrict access "
                "and retention."
            ),
            "mode": self.mode,
            "status": self.execution_status,
            "generated_at": self.generated_at.isoformat(),
            "apply_requested": self.apply_requested,
            "allow_missing_records": self.allow_missing_records,
            "apply_blocked": self.apply_blocked,
            "apply_blocked_reasons": self.apply_blocked_reasons,
            "counts": {
                "total": len(self.entries),
                "conflicts": self.conflict_count,
                "review_required_missing_records": self.review_required_count,
                "reset_email_failures": self.reset_failure_count,
                "by_disposition": dict(sorted(counts.items())),
                "password_reset_required": len(reset_candidates),
            },
            "password_reset_candidates": reset_candidates,
            "password_only_users_needing_reset": password_only_users,
            "users": [entry.to_dict() for entry in self.entries],
        }


class PasswordResetSender(Protocol):
    """Subset of NativeAuthService used by an optional reset campaign."""

    async def request_password_reset(self, email: EmailStr) -> None:
        """Issue and send one native password reset email."""


@dataclass(slots=True)
class _PlannedUser:
    firebase: FirebaseUserRecord
    user: User
    identities: tuple[tuple[IdentityProvider, str], ...]
    target_state: AuthMigrationState
    promote_email_verified: bool
    audit: MigrationAuditEntry


class FirebaseIdentityMigrationService:
    """Preflight and reconcile Firebase identities without email auto-linking."""

    def __init__(
        self,
        *,
        user_repository: UserRepository | None = None,
        identity_repository: AuthIdentityRepository | None = None,
        reset_sender: PasswordResetSender | None = None,
    ) -> None:
        self.users = user_repository or UserRepository()
        self.identities = identity_repository or AuthIdentityRepository()
        self.reset_sender = reset_sender

    async def reconcile(
        self,
        firebase_users: list[FirebaseUserRecord],
        *,
        apply: bool = False,
        send_reset_emails: bool = False,
        allow_missing_records: bool = False,
    ) -> MigrationAuditReport:
        """Preflight all records, then optionally apply only a conflict-free plan."""
        if send_reset_emails and not apply:
            raise ValueError("--send-reset-emails requires --apply")
        if allow_missing_records and not apply:
            raise ValueError("--allow-missing-records requires --apply")
        if send_reset_emails and self.reset_sender is None:
            raise ValueError("Password reset email delivery is not configured")

        planned, entries = await self._preflight(firebase_users)
        report = MigrationAuditReport(
            mode="apply" if apply else "dry-run",
            generated_at=datetime.now(UTC),
            entries=entries,
            apply_requested=apply,
            allow_missing_records=allow_missing_records,
        )
        if apply:
            if report.conflict_count:
                report.apply_blocked_reasons.append("unresolved_conflicts")
            if report.review_required_count and not allow_missing_records:
                report.apply_blocked_reasons.append(
                    "missing_records_require_operator_acceptance"
                )
            report.apply_blocked = bool(report.apply_blocked_reasons)
        if not apply or report.apply_blocked:
            return report

        for item in planned:
            await self._apply_user(item)
        if send_reset_emails:
            await self._send_reset_campaign(planned)
        return report

    async def _preflight(
        self,
        firebase_users: list[FirebaseUserRecord],
    ) -> tuple[list[_PlannedUser], list[MigrationAuditEntry]]:
        mongo_users = await self.users.get_all()
        users_by_uid: dict[str, list[User]] = defaultdict(list)
        entries: list[MigrationAuditEntry] = []
        for user in mongo_users:
            if user.firebase_uid:
                users_by_uid[user.firebase_uid].append(user)
            elif (
                user.auth_migration_state is not AuthMigrationState.NATIVE
                or user.auth_provider.startswith("firebase")
            ):
                entries.append(
                    MigrationAuditEntry(
                        disposition=MigrationDisposition.CONFLICT,
                        firebase_uid=None,
                        mongo_user_id=str(user.id),
                        email=str(user.email),
                        conflicts=["mongo_firebase_uid_missing"],
                    )
                )

        firebase_uid_counts = Counter(record.uid for record in firebase_users)
        seen_firebase_uids: set[str] = set()
        planned: list[_PlannedUser] = []
        planned_subjects: dict[tuple[IdentityProvider, str], str] = {}

        for record in firebase_users:
            uid = record.uid.strip()
            uid_malformed = uid != record.uid
            if not uid or uid_malformed or firebase_uid_counts[record.uid] > 1:
                entries.append(
                    MigrationAuditEntry(
                        disposition=MigrationDisposition.CONFLICT,
                        firebase_uid=record.uid or None,
                        mongo_user_id=None,
                        email=record.email,
                        conflicts=[
                            (
                                "firebase_uid_missing"
                                if not uid
                                else "firebase_uid_malformed"
                                if uid_malformed
                                else "duplicate_firebase_record_uid"
                            )
                        ],
                    )
                )
                continue
            seen_firebase_uids.add(uid)
            matches = users_by_uid.get(uid, [])
            if not matches:
                entries.append(
                    MigrationAuditEntry(
                        disposition=MigrationDisposition.MISSING_MONGO_USER,
                        firebase_uid=uid,
                        mongo_user_id=None,
                        email=record.email,
                        actions=["operator_review_no_email_link_attempted"],
                    )
                )
                continue
            if len(matches) > 1:
                entries.append(
                    MigrationAuditEntry(
                        disposition=MigrationDisposition.CONFLICT,
                        firebase_uid=uid,
                        mongo_user_id=None,
                        email=record.email,
                        conflicts=["duplicate_mongo_firebase_uid"],
                    )
                )
                continue
            item = await self._plan_matched_user(
                record,
                matches[0],
                planned_subjects,
            )
            planned.append(item)
            entries.append(item.audit)

        for uid, users in users_by_uid.items():
            if uid in seen_firebase_uids:
                continue
            for user in users:
                entries.append(
                    MigrationAuditEntry(
                        disposition=MigrationDisposition.MISSING_FIREBASE_RECORD,
                        firebase_uid=uid,
                        mongo_user_id=str(user.id),
                        email=str(user.email),
                        actions=["operator_review_firebase_record_missing"],
                    )
                )
        return planned, entries

    async def _plan_matched_user(
        self,
        record: FirebaseUserRecord,
        user: User,
        planned_subjects: dict[tuple[IdentityProvider, str], str],
    ) -> _PlannedUser:
        user_id = require_object_id(user.id)
        conflicts: list[str] = []
        actions: list[str] = []
        firebase_email = _canonical_email(record.email)
        mongo_email = _canonical_email(str(user.email))
        if firebase_email is None:
            conflicts.append("firebase_email_missing")
        elif firebase_email != mongo_email:
            conflicts.append("firebase_mongo_email_mismatch")

        google_subjects, malformed_google = _google_subjects(record.provider_data)
        if malformed_google:
            conflicts.append("google_provider_subject_missing_or_malformed")
        if len(google_subjects) > 1:
            conflicts.append("multiple_google_provider_subjects")

        expected = [(IdentityProvider.FIREBASE, record.uid)]
        if len(google_subjects) == 1:
            expected.append((IdentityProvider.GOOGLE, next(iter(google_subjects))))

        existing_for_user = await self.identities.list_by_user(user_id)
        for provider, subject in expected:
            existing = await self.identities.get_by_provider_subject(provider, subject)
            if existing is not None and existing.user_id != user_id:
                conflicts.append(f"{provider.value}_subject_linked_to_different_user")
            if (
                existing is not None
                and existing.provider_email is not None
                and _canonical_email(existing.provider_email) != mongo_email
            ):
                conflicts.append(
                    f"inconsistent_existing_{provider.value}_email_snapshot"
                )
            same_provider = [
                identity
                for identity in existing_for_user
                if identity.provider is provider
            ]
            if any(identity.provider_subject != subject for identity in same_provider):
                conflicts.append(f"inconsistent_existing_{provider.value}_identity")
            owner = planned_subjects.get((provider, subject))
            if owner is not None and owner != str(user_id):
                conflicts.append(f"duplicate_planned_{provider.value}_subject")
            planned_subjects[(provider, subject)] = str(user_id)
            if existing is None:
                actions.append(f"create_{provider.value}_identity")

        has_google = len(google_subjects) == 1 or any(
            identity.provider is IdentityProvider.GOOGLE
            for identity in existing_for_user
        )
        target_state = _target_migration_state(user, has_google)
        if target_state is not user.auth_migration_state:
            actions.append(f"set_migration_state_{target_state.value}")
        promote_verified = record.email_verified and not user.email_verified
        if promote_verified:
            actions.append("promote_email_verified")
        needs_reset = (
            record.has_password_credential
            and user.password_hash is None
            and user.is_active
            and firebase_email is not None
        )
        password_only = needs_reset and not has_google
        disposition = (
            MigrationDisposition.CONFLICT
            if conflicts
            else MigrationDisposition.READY
            if actions
            else MigrationDisposition.UNCHANGED
        )
        audit = MigrationAuditEntry(
            disposition=disposition,
            firebase_uid=record.uid,
            mongo_user_id=str(user_id),
            email=mongo_email,
            actions=actions,
            conflicts=sorted(set(conflicts)),
            password_reset_required=needs_reset,
            password_only_firebase_user=password_only,
        )
        return _PlannedUser(
            firebase=record,
            user=user,
            identities=tuple(expected),
            target_state=target_state,
            promote_email_verified=promote_verified,
            audit=audit,
        )

    async def _apply_user(self, item: _PlannedUser) -> None:
        user_id = require_object_id(item.user.id)
        for provider, subject in item.identities:
            existing = await self.identities.get_by_provider_subject(provider, subject)
            if existing is None:
                try:
                    await self.identities.create(
                        AuthIdentity(
                            user_id=user_id,
                            provider=provider,
                            provider_subject=subject,
                            provider_email=_canonical_email(item.firebase.email),
                        )
                    )
                except DuplicateKeyError:
                    winner = await self.identities.get_by_provider_subject(
                        provider,
                        subject,
                    )
                    if winner is None or winner.user_id != user_id:
                        item.audit.conflicts.append(
                            f"{provider.value}_identity_race_conflict"
                        )
                        item.audit.disposition = MigrationDisposition.CONFLICT
                        return

        changed = False
        if item.user.auth_migration_state is not item.target_state:
            item.user.auth_migration_state = item.target_state
            changed = True
        if item.promote_email_verified:
            item.user.email_verified = True
            changed = True
        if changed:
            item.user.updated_at = datetime.now(UTC)
            await item.user.save()
        item.audit.disposition = (
            MigrationDisposition.APPLIED
            if item.audit.actions
            else MigrationDisposition.UNCHANGED
        )

    async def _send_reset_campaign(self, planned: list[_PlannedUser]) -> None:
        if self.reset_sender is None:
            raise ValueError("Password reset email delivery is not configured")
        for item in planned:
            if not item.audit.password_reset_required or item.audit.conflicts:
                continue
            try:
                await self.reset_sender.request_password_reset(item.user.email)
                item.audit.reset_email_status = ResetEmailStatus.SENT
            except Exception as exc:
                item.audit.reset_email_status = ResetEmailStatus.FAILED
                item.audit.reset_email_error = type(exc).__name__


def _canonical_email(email: str | None) -> str | None:
    if email is None or not email.strip():
        return None
    return email.strip().lower()


def _google_subjects(
    providers: tuple[FirebaseProviderRecord, ...],
) -> tuple[set[str], bool]:
    subjects: set[str] = set()
    malformed = False
    for provider in providers:
        if provider.provider_id != "google.com":
            continue
        subject = provider.uid.strip()
        if not subject or subject != provider.uid:
            malformed = True
        else:
            subjects.add(subject)
    return subjects, malformed


def _target_migration_state(
    user: User,
    has_google_identity: bool,
) -> AuthMigrationState:
    if user.auth_migration_state is AuthMigrationState.NATIVE:
        return AuthMigrationState.NATIVE
    if user.auth_migration_state is AuthMigrationState.DUAL:
        return AuthMigrationState.DUAL
    if user.password_hash is not None or has_google_identity:
        return AuthMigrationState.DUAL
    return AuthMigrationState.FIREBASE_ONLY
