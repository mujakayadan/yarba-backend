"""Add encrypted apply-credentials field on profiles.

Migration created at: 2026-06-18T00:00:00
"""

from __future__ import annotations

from core.database.migrations.migration_manager import Migration
from core.database.migrations.schema_helpers import ensure_validator

_PROFILES_APPLY_CREDENTIALS_FIELDS = {
    "$jsonSchema": {
        "bsonType": "object",
        "properties": {
            "application_preferences": {"bsonType": "object"},
            "demographics_encrypted": {"bsonType": ["string", "null"]},
            "apply_credentials_encrypted": {"bsonType": ["string", "null"]},
        },
    }
}


class ApplyCredentialsMigration(Migration):
    """Allow encrypted careers-site passwords on profiles."""

    def upgrade(self) -> None:
        if "profiles" in self.db.list_collection_names():
            ensure_validator(
                self.db,
                "profiles",
                _PROFILES_APPLY_CREDENTIALS_FIELDS,
                validation_level="moderate",
            )

    def downgrade(self) -> None:
        pass
