"""MongoDB migration manager for tracking schema changes."""

import importlib.util
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pymongo import MongoClient
from pymongo.database import Database

from config.logging_config import get_logger

logger = get_logger(__name__)


class Migration:
    """Base class for all migrations."""

    def __init__(self, db: Database):
        """Initialize the migration with a database connection.

        Args:
            db: MongoDB database connection
        """
        self.db = db
        self.description = self.__class__.__doc__ or ""

    def upgrade(self) -> None:
        """Apply the migration."""
        raise NotImplementedError("Each migration must implement the upgrade method")

    def downgrade(self) -> None:
        """Revert the migration."""
        raise NotImplementedError("Each migration must implement the downgrade method")


class MigrationManager:
    """Manager for handling database migrations."""

    MIGRATION_COLLECTION = "migrations"
    MIGRATION_PATTERN = r"^(\d{14})_(.+)\.py$"

    def __init__(
        self,
        mongo_uri: str,
        database_name: str,
        migrations_dir: str = "core/database/migrations",
    ):
        """Initialize the migration manager.

        Args:
            mongo_uri: MongoDB connection URI
            database_name: Name of the database to migrate
            migrations_dir: Directory containing migration files
        """
        self.mongo_uri = mongo_uri
        self.database_name = database_name
        self.migrations_dir = Path(migrations_dir)
        self.client = None
        self.db = None

    def connect(self) -> None:
        """Connect to the MongoDB database."""
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.database_name]
        logger.info(f"Connected to database: {self.database_name}")

    def disconnect(self) -> None:
        """Disconnect from the MongoDB database."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from database")

    def get_applied_migrations(self) -> Dict[str, datetime]:
        """Get all migrations that have been applied to the database.

        Returns:
            Dict mapping migration versions to the datetime they were applied
        """
        applied = {}
        for doc in self.db[self.MIGRATION_COLLECTION].find().sort("version", 1):
            applied[doc["version"]] = doc["applied_at"]
        return applied

    def get_available_migrations(self) -> Dict[str, Path]:
        """Get all available migration files.

        Returns:
            Dict mapping migration versions to file paths
        """
        available = {}
        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return available

        for file_path in self.migrations_dir.glob("*.py"):
            if (
                file_path.name == "__init__.py"
                or file_path.name == "migration_manager.py"
            ):
                continue

            match = re.match(self.MIGRATION_PATTERN, file_path.name)
            if match:
                version = match.group(1)
                available[version] = file_path
            else:
                logger.warning(f"Invalid migration filename: {file_path.name}")

        return available

    def load_migration(self, version: str, file_path: Path) -> Optional[Migration]:
        """Load a migration class from a file.

        Args:
            version: Migration version
            file_path: Path to the migration file

        Returns:
            Migration instance or None if loading failed
        """
        try:
            module_name = f"migration_{version}"
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if not spec or not spec.loader:
                logger.error(f"Could not load migration spec: {file_path}")
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Find the Migration class in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, Migration)
                    and attr is not Migration
                ):
                    return attr(self.db)

            logger.error(f"No Migration class found in {file_path}")
            return None
        except Exception as e:
            logger.error(f"Error loading migration {version}: {e}")
            return None

    def mark_migration_applied(self, version: str, description: str) -> None:
        """Mark a migration as applied in the database.

        Args:
            version: Migration version
            description: Migration description
        """
        self.db[self.MIGRATION_COLLECTION].update_one(
            {"version": version},
            {
                "$set": {
                    "version": version,
                    "description": description,
                    "applied_at": datetime.utcnow(),
                }
            },
            upsert=True,
        )
        logger.info(f"Marked migration {version} as applied")

    def mark_migration_reverted(self, version: str) -> None:
        """Mark a migration as reverted in the database.

        Args:
            version: Migration version
        """
        self.db[self.MIGRATION_COLLECTION].delete_one({"version": version})
        logger.info(f"Marked migration {version} as reverted")

    def create_migration(self, description: str) -> str:
        """Create a new migration file.

        Args:
            description: Short description of the migration

        Returns:
            Path to the created migration file
        """
        # Create migrations directory if it doesn't exist
        os.makedirs(self.migrations_dir, exist_ok=True)

        # Generate version based on current timestamp
        version = datetime.utcnow().strftime("%Y%m%d%H%M%S")

        # Convert description to snake_case for filename
        filename = f"{version}_{description.lower().replace(' ', '_')}.py"
        file_path = self.migrations_dir / filename

        # Create migration file from template
        with open(file_path, "w") as f:
            f.write(
                f'''"""
{description}

Migration created at: {datetime.utcnow().isoformat()}
"""

from pymongo.database import Database
from core.database.migrations.migration_manager import Migration


class {description.title().replace(" ", "")}Migration(Migration):
    """
    {description}
    """

    def upgrade(self) -> None:
        """Apply the migration."""
        # TODO: Implement the migration
        # Example:
        # self.db.users.update_many(
        #     {"email": {"$exists": False}},
        #     {"$set": {"email": ""}}
        # )
        pass

    def downgrade(self) -> None:
        """Revert the migration."""
        # TODO: Implement the downgrade
        # Example:
        # self.db.users.update_many(
        #     {"email": ""},
        #     {"$unset": {"email": ""}}
        # )
        pass
'''
            )

        logger.info(f"Created migration file: {file_path}")
        return str(file_path)

    def run_migrations(self, target_version: Optional[str] = None) -> None:
        """Run all pending migrations up to the target version.

        Args:
            target_version: Target migration version, or None for latest
        """
        try:
            self.connect()

            # Get applied and available migrations
            applied = self.get_applied_migrations()
            available = self.get_available_migrations()

            # Determine migrations to apply
            versions_to_apply = []
            for version in sorted(available.keys()):
                if version not in applied and (
                    target_version is None or version <= target_version
                ):
                    versions_to_apply.append(version)

            if not versions_to_apply:
                logger.info("No migrations to apply")
                return

            logger.info(f"Applying {len(versions_to_apply)} migration(s)")

            # Apply migrations
            for version in versions_to_apply:
                file_path = available[version]
                migration = self.load_migration(version, file_path)

                if migration:
                    logger.info(
                        f"Applying migration {version}: {migration.description}"
                    )
                    migration.upgrade()
                    self.mark_migration_applied(version, migration.description)
                else:
                    logger.error(f"Failed to load migration {version}")
                    break

            logger.info("Migration complete")

        finally:
            self.disconnect()

    def revert_migrations(self, target_version: Optional[str] = None) -> None:
        """Revert migrations down to the target version.

        Args:
            target_version: Target migration version, or None to revert all
        """
        try:
            self.connect()

            # Get applied and available migrations
            applied = self.get_applied_migrations()
            available = self.get_available_migrations()

            # Determine migrations to revert
            versions_to_revert = []
            for version in sorted(applied.keys(), reverse=True):
                if target_version is None or version > target_version:
                    if version in available:
                        versions_to_revert.append(version)
                    else:
                        logger.warning(
                            f"Applied migration {version} not found in files"
                        )

            if not versions_to_revert:
                logger.info("No migrations to revert")
                return

            logger.info(f"Reverting {len(versions_to_revert)} migration(s)")

            # Revert migrations
            for version in versions_to_revert:
                file_path = available[version]
                migration = self.load_migration(version, file_path)

                if migration:
                    logger.info(
                        f"Reverting migration {version}: {migration.description}"
                    )
                    migration.downgrade()
                    self.mark_migration_reverted(version)
                else:
                    logger.error(f"Failed to load migration {version}")
                    break

            logger.info("Reversion complete")

        finally:
            self.disconnect()

    def show_status(self) -> List[Dict[str, Any]]:
        """Show the status of all migrations.

        Returns:
            List of migration status dictionaries
        """
        try:
            self.connect()

            # Get applied and available migrations
            applied = self.get_applied_migrations()
            available = self.get_available_migrations()

            # Combine information
            migrations = []

            # First add available migrations
            for version, file_path in sorted(available.items()):
                migration = self.load_migration(version, file_path)
                description = migration.description if migration else "Unknown"

                migrations.append(
                    {
                        "version": version,
                        "description": description,
                        "filename": file_path.name,
                        "applied": version in applied,
                        "applied_at": applied.get(version),
                    }
                )

            # Then add applied migrations that are not available
            for version, applied_at in applied.items():
                if version not in available:
                    migrations.append(
                        {
                            "version": version,
                            "description": "Unknown (file missing)",
                            "filename": None,
                            "applied": True,
                            "applied_at": applied_at,
                        }
                    )

            return migrations

        finally:
            self.disconnect()


def main():
    """Command-line interface for the migration manager."""
    import argparse

    parser = argparse.ArgumentParser(description="MongoDB migration manager")
    parser.add_argument("--uri", required=True, help="MongoDB connection URI")
    parser.add_argument("--db", required=True, help="Database name")
    parser.add_argument(
        "--dir", default="core/database/migrations", help="Migrations directory"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # create command
    create_parser = subparsers.add_parser("create", help="Create a new migration")
    create_parser.add_argument("description", help="Migration description")

    # migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Run migrations")
    migrate_parser.add_argument("--target", help="Target migration version")

    # revert command
    revert_parser = subparsers.add_parser("revert", help="Revert migrations")
    revert_parser.add_argument("--target", help="Target migration version")

    # status command
    subparsers.add_parser("status", help="Show migration status")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    manager = MigrationManager(args.uri, args.db, args.dir)

    if args.command == "create":
        manager.create_migration(args.description)
    elif args.command == "migrate":
        manager.run_migrations(args.target)
    elif args.command == "revert":
        manager.revert_migrations(args.target)
    elif args.command == "status":
        migrations = manager.show_status()

        # Print status table
        print(f"{'Version':<15} {'Applied':<10} {'Description':<50}")
        print("-" * 75)

        for migration in migrations:
            applied = (
                f"{migration['applied_at']:%Y-%m-%d %H:%M}"
                if migration["applied"]
                else "No"
            )
            print(
                f"{migration['version']:<15} {applied:<10} {migration['description'][:50]}"
            )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
