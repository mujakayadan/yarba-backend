#!/usr/bin/env python3
"""Run MongoDB schema migrations using environment-backed connection settings."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.logging_config import configure_logging
from core.database.migrations.migration_manager import MigrationManager


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        print(f"{name} is required", file=sys.stderr)
        sys.exit(1)
    return value


def _database_name() -> str:
    return os.environ.get("MONGODB_DATABASE") or _require_env("MONGODB_DB")


def _build_manager(
    migrations_dir: str = "core/database/migrations",
) -> MigrationManager:
    return MigrationManager(
        mongo_uri=_require_env("MONGODB_URI"),
        database_name=_database_name(),
        migrations_dir=migrations_dir,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="MongoDB migration manager")
    parser.add_argument(
        "--dir",
        default="core/database/migrations",
        help="Migrations directory",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create a new migration")
    create_parser.add_argument("description", help="Migration description")

    migrate_parser = subparsers.add_parser("migrate", help="Run pending migrations")
    migrate_parser.add_argument("--target", help="Target migration version")

    revert_parser = subparsers.add_parser("revert", help="Revert migrations")
    revert_parser.add_argument("--target", help="Target migration version")

    subparsers.add_parser("status", help="Show migration status")

    args = parser.parse_args()
    configure_logging()
    manager = _build_manager(migrations_dir=args.dir)

    if args.command == "create":
        path = manager.create_migration(args.description)
        print(path)
    elif args.command == "migrate":
        try:
            manager.run_migrations(args.target)
        except RuntimeError:
            sys.exit(1)
    elif args.command == "revert":
        manager.revert_migrations(args.target)
    elif args.command == "status":
        migrations = manager.show_status()
        print(f"{'Version':<15} {'Applied':<10} {'Description':<50}")
        print("-" * 75)
        for migration in migrations:
            applied = "Yes" if migration["applied"] else "No"
            print(
                f"{migration['version']:<15} {applied:<10} {migration['description']:<50}"
            )


if __name__ == "__main__":
    main()
