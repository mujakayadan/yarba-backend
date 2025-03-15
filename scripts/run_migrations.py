#!/usr/bin/env python
"""
Script to run MongoDB migrations for the RBT database.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.database.migrations.migration_manager import MigrationManager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Run the migrations."""
    # Load environment variables
    load_dotenv()

    # Get MongoDB connection details from environment
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    database_name = os.getenv("MONGODB_DATABASE", "rbt")
    migrations_dir = os.getenv("MIGRATIONS_DIR", "core/database/migrations")

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run MongoDB migrations")
    parser.add_argument(
        "command",
        choices=["create", "migrate", "revert", "status"],
        help="Command to run",
    )
    parser.add_argument(
        "--description",
        help="Description for new migration (required for 'create' command)",
    )
    parser.add_argument(
        "--target",
        help="Target migration version (optional for 'migrate' and 'revert' commands)",
    )

    args = parser.parse_args()

    # Create migration manager
    manager = MigrationManager(mongo_uri, database_name, migrations_dir)

    # Run the specified command
    if args.command == "create":
        if not args.description:
            parser.error("--description is required for 'create' command")
        manager.create_migration(args.description)
    elif args.command == "migrate":
        manager.run_migrations(args.target)
    elif args.command == "revert":
        manager.revert_migrations(args.target)
    elif args.command == "status":
        migrations = manager.show_status()

        # Print status table
        print(f"{'Version':<15} {'Applied':<20} {'Description':<50}")
        print("-" * 85)

        for migration in migrations:
            applied = (
                f"{migration['applied_at']:%Y-%m-%d %H:%M:%S}"
                if migration["applied"]
                else "No"
            )
            print(
                f"{migration['version']:<15} {applied:<20} {migration['description'][:50]}"
            )


if __name__ == "__main__":
    main()
