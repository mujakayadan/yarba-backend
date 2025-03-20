# MongoDB Migrations

This directory contains database migrations for the RBT application. Migrations are used to track schema changes and data transformations over time.

## Migration Structure

Each migration file follows the naming convention `YYYYMMDDHHMMSS_description.py` and contains a class that extends the `Migration` base class. The migration class must implement two methods:

- `upgrade()`: Apply the migration
- `downgrade()`: Revert the migration

Example:

```python
from pymongo.database import Database
from core.database.migrations.migration_manager import Migration


class ExampleMigration(Migration):
    """
    Example migration description
    """

    def upgrade(self) -> None:
        """Apply the migration."""
        # Add a new field to all users
        self.db.users.update_many(
            {"email_verified": {"$exists": False}},
            {"$set": {"email_verified": False}}
        )

    def downgrade(self) -> None:
        """Revert the migration."""
        # Remove the field
        self.db.users.update_many(
            {},
            {"$unset": {"email_verified": ""}}
        )
```

## Running Migrations

Use the `scripts/run_migrations.py` script to manage migrations:

```bash
# Create a new migration
poetry run python scripts/run_migrations.py create --description "add email verification"

# Run all pending migrations
poetry run python scripts/run_migrations.py migrate

# Revert to a specific migration
poetry run python scripts/run_migrations.py revert --target 20240620000000

# Show migration status
poetry run python scripts/run_migrations.py status
```

## Migration Tracking

Migrations are tracked in the `migrations` collection in the database. Each applied migration is recorded with:

- `version`: The timestamp from the filename
- `description`: The migration description
- `applied_at`: When the migration was applied

## Existing Migrations

1. `20240313_initial.py` - Initial database setup
2. `20240620000000_initial_schema.py` - Initial schema setup for RBT database
3. `20240621000000_update_models.py` - Update User, Profile, and Portfolio models

## Best Practices

1. **Always include both upgrade and downgrade methods**: This allows for rolling back changes if needed.
2. **Keep migrations small and focused**: Each migration should do one thing well.
3. **Use descriptive names**: The migration filename should clearly indicate what it does.
4. **Test migrations thoroughly**: Especially on a copy of production data before applying to production.
5. **Document schema changes**: Update the entity relationship diagram when schema changes are made.
6. **Version control**: Always commit migration files to version control.

## Initial Setup

To set up a new database with the initial schema:

```bash
poetry run python scripts/run_migrations.py migrate
```

This will apply the initial migration that creates all collections, validators, and indexes.

## Recent Migrations

### 20240623000000_fix_portfolio_user_id.py

This migration fixes two issues:

1. Converts string `user_id` values in the portfolios collection to proper `ObjectId` values
2. Removes the deprecated `professional_title` field from all portfolios

To run this migration:

```bash
# Navigate to the project root
cd /path/to/resume_builder

# Run the migration
poetry run python -m core.database.migrations.migration_manager migrate
```

This ensures consistency between the Pydantic model (which expects `PydanticObjectId`) and the database schema (which should store `ObjectId` values).
