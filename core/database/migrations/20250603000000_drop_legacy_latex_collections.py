"""
Drop legacy LaTeX MongoDB collections.

LaTeX preambles and section snippets live in templates/latex/*.tex and
core/latex/processors/; preambles and tex_headers collections are unused.

Migration created at: 2025-06-03T00:00:00
"""

from core.database.migrations.migration_manager import Migration

_LEGACY_LATEX_COLLECTIONS = ("preambles", "tex_headers")


class DropLegacyLatexCollectionsMigration(Migration):
    """Remove unused preambles and tex_headers collections."""

    def upgrade(self) -> None:
        for name in _LEGACY_LATEX_COLLECTIONS:
            if name in self.db.list_collection_names():
                self.db[name].drop()

    def downgrade(self) -> None:
        pass
