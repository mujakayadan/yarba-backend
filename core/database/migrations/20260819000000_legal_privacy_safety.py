"""Add legal evidence, safety moderation, and account data-rights storage."""

from pymongo import ASCENDING, DESCENDING, IndexModel

from core.database.migrations.migration_manager import Migration
from core.database.migrations.schema_helpers import (
    ensure_collection,
    ensure_index_models,
)


class LegalPrivacySafetyMigration(Migration):
    """Create durable collections and moderation fields."""

    def upgrade(self) -> None:
        legal_documents = ensure_collection(self.db, "legal_document_versions")
        ensure_index_models(
            legal_documents,
            [
                IndexModel(
                    [("document_type", ASCENDING), ("version", ASCENDING)],
                    unique=True,
                ),
                IndexModel([("document_type", ASCENDING), ("is_current", ASCENDING)]),
            ],
        )
        acceptances = ensure_collection(self.db, "legal_acceptances")
        ensure_index_models(
            acceptances,
            [
                IndexModel([("user_id", ASCENDING)]),
                IndexModel(
                    [
                        ("user_id", ASCENDING),
                        ("document_type", ASCENDING),
                        ("document_version", ASCENDING),
                    ],
                    unique=True,
                ),
                IndexModel(
                    [
                        ("user_id", ASCENDING),
                        ("document_type", ASCENDING),
                        ("accepted_at", DESCENDING),
                    ]
                ),
            ],
        )
        reports = ensure_collection(self.db, "abuse_reports")
        ensure_index_models(
            reports,
            [
                IndexModel([("status", ASCENDING)]),
                IndexModel([("category", ASCENDING)]),
                IndexModel([("portfolio_website_id", ASCENDING)]),
                IndexModel([("due_at", ASCENDING)]),
                IndexModel([("retention_expires_at", ASCENDING)], expireAfterSeconds=0),
            ],
        )
        audits = ensure_collection(self.db, "moderation_audit_events")
        ensure_index_models(
            audits,
            [
                IndexModel([("target_id", ASCENDING)]),
                IndexModel([("report_id", ASCENDING)]),
                IndexModel([("retention_expires_at", ASCENDING)], expireAfterSeconds=0),
            ],
        )
        exports = ensure_collection(self.db, "account_export_requests")
        ensure_index_models(
            exports,
            [
                IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)]),
                IndexModel([("status", ASCENDING)]),
                IndexModel([("expires_at", ASCENDING)]),
            ],
        )
        deletions = ensure_collection(self.db, "account_deletion_requests")
        ensure_index_models(
            deletions,
            [
                IndexModel([("user_id", ASCENDING), ("requested_at", DESCENDING)]),
                IndexModel([("status", ASCENDING), ("scheduled_for", ASCENDING)]),
            ],
        )
        self.db.portfolio_websites.update_many(
            {"moderation_status": {"$exists": False}},
            {
                "$set": {
                    "moderation_status": "active",
                    "moderation_message": None,
                    "clean_redeploy_required": False,
                }
            },
        )
        self.db.users.update_many(
            {"moderation_strike_count": {"$exists": False}},
            {
                "$set": {
                    "moderation_strike_count": 0,
                    "copyright_strike_count": 0,
                    "repeat_infringer": False,
                }
            },
        )

    def downgrade(self) -> None:
        for name in (
            "legal_document_versions",
            "legal_acceptances",
            "abuse_reports",
            "moderation_audit_events",
            "account_export_requests",
            "account_deletion_requests",
        ):
            if name in self.db.list_collection_names():
                self.db[name].drop()
        self.db.portfolio_websites.update_many(
            {},
            {
                "$unset": {
                    "moderation_status": "",
                    "moderation_message": "",
                    "suspended_at": "",
                    "suspension_reason": "",
                    "clean_redeploy_required": "",
                }
            },
        )
        self.db.users.update_many(
            {},
            {
                "$unset": {
                    "moderation_strike_count": "",
                    "copyright_strike_count": "",
                    "repeat_infringer": "",
                }
            },
        )
