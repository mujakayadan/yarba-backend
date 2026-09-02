#!/usr/bin/env python
"""Dry-run-first Firebase identity reconciliation CLI.

Audit reports contain user IDs and email addresses and must be handled as
sensitive operator artifacts. They never contain credentials or raw tokens.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from firebase_admin import auth

from config.settings import settings
from core.auth.firebase import FirebaseAuth
from core.database.init import init_db
from core.services.email_clients.resend_client import ResendClient
from core.services.firebase_identity_migration_service import (
    FirebaseIdentityMigrationService,
    FirebaseProviderRecord,
    FirebaseUserRecord,
    MigrationAuditReport,
)
from core.services.native_auth_service import NativeAuthService


@dataclass(frozen=True, slots=True)
class _FirebaseProviderSnapshot:
    provider_id: str
    uid: str


async def read_firebase_users() -> list[FirebaseUserRecord]:
    """Read all Firebase users through Admin SDK pagination off the event loop."""
    records: list[FirebaseUserRecord] = []
    page_token: str | None = None
    while True:
        page = await asyncio.to_thread(
            auth.list_users,
            page_token=page_token,
            max_results=1000,
        )
        for user in page.users:
            providers = cast(
                tuple[FirebaseProviderRecord, ...],
                tuple(
                    _FirebaseProviderSnapshot(
                        provider_id=str(provider.provider_id),
                        uid=str(provider.uid or ""),
                    )
                    for provider in user.provider_data
                ),
            )
            records.append(
                FirebaseUserRecord(
                    uid=str(user.uid or ""),
                    email=str(user.email) if user.email else None,
                    email_verified=bool(user.email_verified),
                    has_password_credential=user.password_hash is not None,
                    provider_data=providers,
                )
            )
        page_token = page.next_page_token
        if not page_token:
            return records


def write_report(report: MigrationAuditReport, path: Path) -> None:
    """Write a deterministic, credential-free JSON audit report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _build_migration_email_sender() -> NativeAuthService:
    api_key = settings.resend.api_key.get_secret_value()
    if not api_key:
        raise ValueError("Resend is not configured; migration emails cannot be sent")
    resend_client = ResendClient(
        api_key=api_key,
        from_address=settings.resend.from_address,
    )
    return NativeAuthService(resend_client=resend_client)


async def run(
    *,
    report_path: Path,
    apply: bool,
    send_migration_emails: bool,
    allow_missing_records: bool,
) -> int:
    """Execute reconciliation and return a process exit code."""
    if send_migration_emails and not apply:
        raise ValueError("--send-migration-emails requires --apply")
    if allow_missing_records and not apply:
        raise ValueError("--allow-missing-records requires --apply")
    client = await init_db()
    if client is None:
        raise RuntimeError("MongoDB initialization failed")
    if not FirebaseAuth.initialize():
        raise RuntimeError("Firebase Admin initialization failed")

    migration_email_sender = (
        _build_migration_email_sender() if send_migration_emails else None
    )
    firebase_users = await read_firebase_users()
    service = FirebaseIdentityMigrationService(
        migration_email_sender=migration_email_sender
    )
    report = await service.reconcile(
        firebase_users,
        apply=apply,
        send_migration_emails=send_migration_emails,
        allow_missing_records=allow_missing_records,
    )
    write_report(report, report_path)
    if report.apply_blocked:
        summary = (
            f"Reconciliation apply blocked: {', '.join(report.apply_blocked_reasons)}."
        )
    else:
        summary = f"Reconciliation status: {report.execution_status}."
    print(
        f"{summary} {len(report.entries)} records, "
        f"{report.conflict_count} conflicts, "
        f"{report.review_required_count} review-required missing records, "
        f"{report.migration_email_failure_count} migration email failures."
    )
    print(f"Sensitive audit report written to: {report_path}")
    return 1 if report.has_failures else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reconcile Firebase identities into MongoDB. Dry-run is the default."
        )
    )
    parser.add_argument(
        "--report",
        type=Path,
        required=True,
        help="Required path for the sensitive JSON audit report",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply a conflict-free reconciliation plan",
    )
    parser.add_argument(
        "--send-migration-emails",
        action="store_true",
        help="Send durable password migration invitations; requires --apply",
    )
    parser.add_argument(
        "--allow-missing-records",
        action="store_true",
        help=(
            "Explicitly accept missing Mongo/Firebase review dispositions; "
            "requires --apply"
        ),
    )
    args = parser.parse_args()
    if args.send_migration_emails and not args.apply:
        parser.error("--send-migration-emails requires --apply")
    if args.allow_missing_records and not args.apply:
        parser.error("--allow-missing-records requires --apply")
    return args


def main() -> None:
    args = parse_args()
    try:
        exit_code = asyncio.run(
            run(
                report_path=args.report,
                apply=args.apply,
                send_migration_emails=args.send_migration_emails,
                allow_missing_records=args.allow_missing_records,
            )
        )
    except (RuntimeError, ValueError) as exc:
        print(f"Reconciliation aborted: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
