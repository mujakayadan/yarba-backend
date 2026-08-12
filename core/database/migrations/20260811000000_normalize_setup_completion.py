"""Normalize legacy setup completion values.

Migration created at: 2026-08-11T00:00:00
"""

from __future__ import annotations

from core.database.migrations.migration_manager import Migration


class NormalizeSetupCompletionMigration(Migration):
    """Use zero as the only completed setup step."""

    def upgrade(self) -> None:
        if "users" not in self.db.list_collection_names():
            return

        self.db["users"].update_many(
            {"current_setup_step": 99},
            {"$set": {"current_setup_step": 0, "is_new_user": False}},
        )

    def downgrade(self) -> None:
        pass
