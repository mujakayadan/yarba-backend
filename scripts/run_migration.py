#!/usr/bin/env python
"""Helper script to run database migrations."""

import argparse
import asyncio
import importlib
import inspect
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.logging_config import configure_logging, get_logger
from core.database import init_db
from core.database.migrations.migration_manager import Migration

# Configure logging
configure_logging()
logger = get_logger("migration_runner")


async def run_migration(migration_name: str = None):
    """Run a specific migration.

    Args:
        migration_name: Name of the migration class to run, e.g., 'fix_mongodb_validation'
                       If None, shows available migrations
    """
    if not migration_name:
        print("Please specify a migration to run. Available migrations:")
        _show_available_migrations()
        return

    migration_file = f"core.database.migrations.{migration_name}"

    try:
        # Import the migration module
        migration_module = importlib.import_module(migration_file)

        # Find the Migration class
        migration_class = None
        for name, obj in inspect.getmembers(migration_module):
            if inspect.isclass(obj) and issubclass(obj, Migration) and obj != Migration:
                migration_class = obj
                break

        if not migration_class:
            logger.error(f"No migration class found in {migration_file}")
            return

        # Initialize the database connection
        from motor.motor_asyncio import AsyncIOMotorClient
        from pymongo.database import Database

        from config.settings import settings

        # Connect to MongoDB directly
        client = AsyncIOMotorClient(settings.mongodb_uri)
        db = client[settings.mongodb_database]

        # Run the migration
        migration = migration_class(db)
        logger.info(f"Running migration: {migration_class.__name__}")
        migration.upgrade()
        logger.info("Migration completed successfully")

    except ImportError:
        logger.error(f"Migration file not found: {migration_file}")
    except Exception as e:
        logger.error(f"Error running migration: {e}")
        import traceback

        traceback.print_exc()


def _show_available_migrations():
    """Show available migrations."""
    migrations_dir = Path(project_root) / "core" / "database" / "migrations"
    for file in migrations_dir.glob("*.py"):
        if file.stem not in ["__init__", "migration_manager"]:
            print(f"  - {file.stem}")


def main():
    """Run the migration tool."""
    parser = argparse.ArgumentParser(description="Run database migrations")
    parser.add_argument(
        "migration", nargs="?", type=str, help="Name of the migration to run"
    )

    args = parser.parse_args()

    asyncio.run(run_migration(args.migration))


if __name__ == "__main__":
    main()
