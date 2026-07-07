"""Application automation collections and profile field validators.

Migration created at: 2026-06-17T00:00:00
"""

from __future__ import annotations

from pymongo import ASCENDING, IndexModel

from core.database.migrations.migration_manager import Migration
from core.database.migrations.schema_helpers import (
    ensure_collection,
    ensure_index_models,
    ensure_indexes,
    ensure_validator,
)

_PROFILES_APPLICATION_FIELDS = {
    "$jsonSchema": {
        "bsonType": "object",
        "properties": {
            "application_preferences": {"bsonType": "object"},
            "demographics_encrypted": {"bsonType": ["string", "null"]},
        },
    }
}


class ApplicationAutomationMigration(Migration):
    """Add agent tokens, job applications, and profile application fields."""

    def upgrade(self) -> None:
        agent_tokens = ensure_collection(self.db, "agent_access_tokens")
        ensure_index_models(
            agent_tokens,
            [
                IndexModel([("token_hash", ASCENDING)], unique=True),
                IndexModel([("user_id", ASCENDING)]),
            ],
        )

        job_apps = ensure_collection(self.db, "job_applications")
        ensure_indexes(job_apps, ["user_id", "status"])

        if "profiles" in self.db.list_collection_names():
            ensure_validator(
                self.db,
                "profiles",
                _PROFILES_APPLICATION_FIELDS,
                validation_level="moderate",
            )

    def downgrade(self) -> None:
        for name in ("agent_access_tokens", "job_applications"):
            if name in self.db.list_collection_names():
                self.db[name].drop()
