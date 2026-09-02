"""Focused tests for safe Firebase identity reconciliation."""

import sys
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from core.auth.password import get_password_hash
from core.auth.types import AuthMigrationState, IdentityProvider
from core.models.auth_identity import AuthIdentity
from core.models.user import User
from core.services.firebase_identity_migration_service import (
    FirebaseIdentityMigrationService,
    FirebaseUserRecord,
    MigrationDisposition,
    MigrationEmailStatus,
)
from core.utils.object_id import require_object_id
from scripts.reconcile_firebase_identities import parse_args, read_firebase_users


@dataclass(frozen=True, slots=True)
class FakeProvider:
    provider_id: str
    uid: str


class FakeMigrationEmailSender:
    def __init__(self, failing_email: str | None = None) -> None:
        self.failing_email = failing_email
        self.sent: list[str] = []

    async def send_password_migration_invitation(self, email) -> None:
        value = str(email)
        if value == self.failing_email:
            raise RuntimeError("simulated delivery failure")
        self.sent.append(value)


async def _legacy_user(
    *,
    username: str,
    email: str,
    firebase_uid: str | None,
    state: AuthMigrationState = AuthMigrationState.FIREBASE_ONLY,
    password_hash: str | None = None,
    email_verified: bool = False,
    auth_provider: str = "firebase.password",
) -> User:
    user = User(
        username=username,
        email=email,
        firebase_uid=firebase_uid,
        auth_provider=auth_provider,
        auth_migration_state=state,
        password_hash=password_hash,
        email_verified=email_verified,
    )
    await user.insert()
    return user


def _firebase_user(
    uid: str,
    email: str | None,
    *providers: FakeProvider,
    email_verified: bool = False,
    has_password_credential: bool = False,
) -> FirebaseUserRecord:
    return FirebaseUserRecord(
        uid=uid,
        email=email,
        email_verified=email_verified,
        has_password_credential=has_password_credential,
        provider_data=providers,
    )


def test_cli_defaults_to_dry_run_and_gates_email_send(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    report_path = tmp_path / "audit.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["reconcile_firebase_identities.py", "--report", str(report_path)],
    )
    args = parse_args()
    assert args.apply is False
    assert args.send_migration_emails is False
    assert args.allow_missing_records is False

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "reconcile_firebase_identities.py",
            "--report",
            str(report_path),
            "--send-migration-emails",
        ],
    )
    with pytest.raises(SystemExit) as invalid:
        parse_args()
    assert invalid.value.code == 2

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "reconcile_firebase_identities.py",
            "--report",
            str(report_path),
            "--allow-missing-records",
        ],
    )
    with pytest.raises(SystemExit) as missing_without_apply:
        parse_args()
    assert missing_without_apply.value.code == 2


@pytest.mark.asyncio
async def test_firebase_adapter_classifies_password_hash_without_provider_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = SimpleNamespace(
        users=[
            SimpleNamespace(
                uid="password-user-uid",
                email="password-user@example.com",
                email_verified=False,
                password_hash=b"redacted-hash-bytes",
                provider_data=[],
            ),
            SimpleNamespace(
                uid="oauth-user-uid",
                email="oauth-user@example.com",
                email_verified=True,
                password_hash=None,
                provider_data=[],
            ),
        ],
        next_page_token=None,
    )
    monkeypatch.setattr(
        "scripts.reconcile_firebase_identities.auth.list_users",
        lambda **_kwargs: page,
    )

    records = await read_firebase_users()

    assert records[0].has_password_credential is True
    assert records[0].provider_data == ()
    assert records[1].has_password_credential is False
    assert "redacted-hash-bytes" not in str(records)


@pytest.mark.asyncio
async def test_dry_run_never_mutates_and_never_matches_by_email(beanie_db) -> None:
    user = await _legacy_user(
        username="legacy",
        email="same@example.com",
        firebase_uid="mongo-uid",
    )
    report = await FirebaseIdentityMigrationService().reconcile(
        [_firebase_user("different-firebase-uid", "same@example.com")],
    )

    assert await AuthIdentity.find_all().count() == 0
    unchanged = await User.get(user.id)
    assert unchanged is not None
    assert unchanged.auth_migration_state is AuthMigrationState.FIREBASE_ONLY
    assert {entry.disposition for entry in report.entries} == {
        MigrationDisposition.MISSING_MONGO_USER,
        MigrationDisposition.MISSING_FIREBASE_RECORD,
    }
    assert report.review_required_count == 2
    assert report.to_dict()["counts"]["review_required_missing_records"] == 2


@pytest.mark.asyncio
async def test_apply_blocks_on_missing_records_until_explicitly_allowed(
    beanie_db,
) -> None:
    clean = await _legacy_user(
        username="clean-reviewed",
        email="clean-reviewed@example.com",
        firebase_uid="clean-reviewed-uid",
    )
    await _legacy_user(
        username="firebase-record-missing",
        email="firebase-record-missing@example.com",
        firebase_uid="firebase-record-missing-uid",
    )
    records = [
        _firebase_user("clean-reviewed-uid", "clean-reviewed@example.com"),
        _firebase_user("mongo-record-missing-uid", "mongo-record-missing@example.com"),
    ]
    service = FirebaseIdentityMigrationService()

    blocked = await service.reconcile(records, apply=True)

    assert blocked.apply_blocked is True
    assert blocked.apply_blocked_reasons == [
        "missing_records_require_operator_acceptance"
    ]
    assert blocked.execution_status == "apply_blocked"
    assert blocked.has_failures is True
    assert await AuthIdentity.find_one({"user_id": clean.id}) is None
    blocked_json = blocked.to_dict()
    assert blocked_json["apply_blocked"] is True
    assert blocked_json["status"] == "apply_blocked"

    allowed = await service.reconcile(
        records,
        apply=True,
        allow_missing_records=True,
    )

    assert allowed.apply_blocked is False
    assert allowed.review_required_count == 2
    assert allowed.execution_status == "applied"
    assert allowed.has_failures is False
    assert await AuthIdentity.find_one({"user_id": clean.id}) is not None


@pytest.mark.asyncio
async def test_apply_is_idempotent_and_uses_google_provider_subject(beanie_db) -> None:
    user = await _legacy_user(
        username="google-user",
        email="Google.User@Example.com",
        firebase_uid="firebase-uid",
    )
    firebase = _firebase_user(
        "firebase-uid",
        "google.user@example.com",
        FakeProvider("google.com", "stable-google-subject"),
        email_verified=True,
    )
    service = FirebaseIdentityMigrationService()

    first = await service.reconcile([firebase], apply=True)
    second = await service.reconcile([firebase], apply=True)

    identities = await AuthIdentity.find({"user_id": user.id}).to_list()
    assert {
        (identity.provider, identity.provider_subject) for identity in identities
    } == {
        (IdentityProvider.FIREBASE, "firebase-uid"),
        (IdentityProvider.GOOGLE, "stable-google-subject"),
    }
    assert all(
        identity.provider_subject not in {"google.user@example.com"}
        for identity in identities
    )
    refreshed = await User.get(user.id)
    assert refreshed is not None
    assert refreshed.email_verified is True
    assert refreshed.auth_migration_state is AuthMigrationState.DUAL
    assert first.conflict_count == second.conflict_count == 0
    assert await AuthIdentity.find_all().count() == 2


@pytest.mark.asyncio
async def test_password_classification_and_state_transitions(beanie_db) -> None:
    password_only = await _legacy_user(
        username="password-only",
        email="password-only@example.com",
        firebase_uid="password-only-uid",
    )
    native_password = await _legacy_user(
        username="native-password",
        email="native-password@example.com",
        firebase_uid="native-password-uid",
        password_hash=get_password_hash("NativePassword123"),
    )
    native_state = await _legacy_user(
        username="native-state",
        email="native-state@example.com",
        firebase_uid="native-state-uid",
        state=AuthMigrationState.NATIVE,
        auth_provider="password",
    )
    records = [
        _firebase_user(
            "password-only-uid",
            "password-only@example.com",
            has_password_credential=True,
        ),
        _firebase_user(
            "native-password-uid",
            "native-password@example.com",
            has_password_credential=True,
        ),
        _firebase_user(
            "native-state-uid",
            "native-state@example.com",
            FakeProvider("google.com", "native-state-google"),
        ),
    ]

    report = await FirebaseIdentityMigrationService().reconcile(records, apply=True)

    password_only_after = await User.get(password_only.id)
    native_password_after = await User.get(native_password.id)
    native_state_after = await User.get(native_state.id)
    assert password_only_after is not None
    assert native_password_after is not None
    assert native_state_after is not None
    assert password_only_after.auth_migration_state is AuthMigrationState.FIREBASE_ONLY
    assert native_password_after.auth_migration_state is AuthMigrationState.DUAL
    assert native_state_after.auth_migration_state is AuthMigrationState.NATIVE
    reset_entries = [entry for entry in report.entries if entry.password_reset_required]
    assert [entry.mongo_user_id for entry in reset_entries] == [str(password_only.id)]
    assert report.to_dict()["password_only_users_needing_reset"] == [
        {
            "mongo_user_id": str(password_only.id),
            "email": "password-only@example.com",
            "migration_email_status": "not_requested",
        }
    ]


@pytest.mark.asyncio
async def test_named_identity_and_email_conflicts_are_not_mutated(beanie_db) -> None:
    clean = await _legacy_user(
        username="clean",
        email="clean@example.com",
        firebase_uid="clean-uid",
    )
    await _legacy_user(
        username="mismatch",
        email="mongo@example.com",
        firebase_uid="mismatch-uid",
    )
    subject_owner = await _legacy_user(
        username="subject-owner",
        email="owner@example.com",
        firebase_uid="owner-uid",
    )
    inconsistent = await _legacy_user(
        username="inconsistent",
        email="inconsistent@example.com",
        firebase_uid="inconsistent-uid",
    )
    await AuthIdentity(
        user_id=require_object_id(subject_owner.id),
        provider=IdentityProvider.GOOGLE,
        provider_subject="claimed-google-subject",
        provider_email="owner@example.com",
    ).insert()
    await AuthIdentity(
        user_id=require_object_id(inconsistent.id),
        provider=IdentityProvider.FIREBASE,
        provider_subject="different-firebase-subject",
        provider_email="inconsistent@example.com",
    ).insert()
    records = [
        _firebase_user("clean-uid", "clean@example.com"),
        _firebase_user("mismatch-uid", "firebase@example.com"),
        _firebase_user(
            "owner-uid",
            "owner@example.com",
            FakeProvider("google.com", ""),
        ),
        _firebase_user(
            "inconsistent-uid",
            "inconsistent@example.com",
            FakeProvider("google.com", "claimed-google-subject"),
        ),
    ]

    report = await FirebaseIdentityMigrationService().reconcile(records, apply=True)

    conflicts = {conflict for entry in report.entries for conflict in entry.conflicts}
    assert "firebase_mongo_email_mismatch" in conflicts
    assert "google_provider_subject_missing_or_malformed" in conflicts
    assert "google_subject_linked_to_different_user" in conflicts
    assert "inconsistent_existing_firebase_identity" in conflicts
    assert (
        await AuthIdentity.find_one(
            {
                "provider": IdentityProvider.FIREBASE,
                "provider_subject": "clean-uid",
            }
        )
        is None
    )
    clean_after = await User.get(clean.id)
    assert clean_after is not None
    assert clean_after.auth_migration_state is AuthMigrationState.FIREBASE_ONLY


@pytest.mark.asyncio
async def test_duplicate_and_missing_uid_conflicts_prevent_apply(beanie_db) -> None:
    await _legacy_user(
        username="duplicate-a",
        email="duplicate-a@example.com",
        firebase_uid="duplicate-mongo-uid",
    )
    await _legacy_user(
        username="duplicate-b",
        email="duplicate-b@example.com",
        firebase_uid="duplicate-mongo-uid",
    )
    await _legacy_user(
        username="missing-uid",
        email="missing-uid@example.com",
        firebase_uid=None,
    )
    clean = await _legacy_user(
        username="clean-duplicate-run",
        email="clean-duplicate-run@example.com",
        firebase_uid="clean-duplicate-run-uid",
    )
    records = [
        _firebase_user("duplicate-mongo-uid", "duplicate-a@example.com"),
        _firebase_user("duplicate-firebase-uid", "one@example.com"),
        _firebase_user("duplicate-firebase-uid", "two@example.com"),
        _firebase_user(
            "clean-duplicate-run-uid",
            "clean-duplicate-run@example.com",
        ),
    ]

    report = await FirebaseIdentityMigrationService().reconcile(records, apply=True)

    conflicts = {conflict for entry in report.entries for conflict in entry.conflicts}
    assert "duplicate_mongo_firebase_uid" in conflicts
    assert "duplicate_firebase_record_uid" in conflicts
    assert "mongo_firebase_uid_missing" in conflicts
    assert await AuthIdentity.find_one({"user_id": clean.id}) is None


@pytest.mark.asyncio
async def test_migration_email_gates_and_failure_reporting(beanie_db) -> None:
    successful = await _legacy_user(
        username="reset-success",
        email="reset-success@example.com",
        firebase_uid="reset-success-uid",
    )
    failing = await _legacy_user(
        username="reset-failure",
        email="reset-failure@example.com",
        firebase_uid="reset-failure-uid",
    )
    records = [
        _firebase_user(
            "reset-success-uid",
            "reset-success@example.com",
            has_password_credential=True,
        ),
        _firebase_user(
            "reset-failure-uid",
            "reset-failure@example.com",
            has_password_credential=True,
        ),
    ]
    with pytest.raises(ValueError, match="requires --apply"):
        await FirebaseIdentityMigrationService().reconcile(
            records,
            send_migration_emails=True,
        )
    with pytest.raises(ValueError, match="allow-missing-records requires --apply"):
        await FirebaseIdentityMigrationService().reconcile(
            records,
            allow_missing_records=True,
        )
    with pytest.raises(ValueError, match="not configured"):
        await FirebaseIdentityMigrationService().reconcile(
            records,
            apply=True,
            send_migration_emails=True,
        )

    sender = FakeMigrationEmailSender(failing_email="reset-failure@example.com")
    report = await FirebaseIdentityMigrationService(
        migration_email_sender=sender
    ).reconcile(records, apply=True, send_migration_emails=True)

    assert sender.sent == ["reset-success@example.com"]
    assert report.migration_email_failure_count == 1
    statuses = {entry.email: entry.migration_email_status for entry in report.entries}
    assert statuses["reset-success@example.com"] is MigrationEmailStatus.SENT
    assert statuses["reset-failure@example.com"] is MigrationEmailStatus.FAILED
    assert await AuthIdentity.find_one({"user_id": successful.id}) is not None
    assert await AuthIdentity.find_one({"user_id": failing.id}) is not None
    serialized = str(report.to_dict())
    assert "RuntimeError" in serialized
    assert "reset token" not in serialized.lower()
