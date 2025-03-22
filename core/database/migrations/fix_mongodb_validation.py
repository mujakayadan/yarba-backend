"""
Fix MongoDB validation to handle NULL values

Migration created at: 2025-03-22T02:00:00
"""

from pymongo.database import Database

from core.database.migrations.migration_manager import Migration


class FixMongoDBValidationMigration(Migration):
    """
    Update MongoDB validation to handle NULL values properly in users and profiles collections
    """

    def upgrade(self) -> None:
        """Apply the migration."""
        # Update User collection - allow null values for optional date fields
        self.db.command(
            {
                "collMod": "users",
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["username", "email", "hashed_password"],
                        "properties": {
                            "username": {"bsonType": "string"},
                            "email": {"bsonType": "string"},
                            "hashed_password": {"bsonType": "string"},
                            "is_active": {"bsonType": "bool"},
                            "is_superuser": {"bsonType": "bool"},
                            "email_verified": {"bsonType": "bool"},
                            "last_login": {"bsonType": ["date", "null"]},
                            "login_attempts": {"bsonType": "int"},
                            "account_locked_until": {"bsonType": ["date", "null"]},
                            "reset_password_token": {"bsonType": ["string", "null"]},
                            "reset_password_expires": {"bsonType": ["date", "null"]},
                            "verification_token": {"bsonType": ["string", "null"]},
                            "subscription_status": {"bsonType": "string"},
                            "subscription_expires": {"bsonType": ["date", "null"]},
                            "last_active": {"bsonType": ["date", "null"]},
                            "created_at": {"bsonType": "date"},
                            "updated_at": {"bsonType": "date"},
                        },
                    }
                },
            }
        )

        # Update Profile collection - allow null values for optional string fields
        self.db.command(
            {
                "collMod": "profiles",
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["user_id", "full_name", "email"],
                        "properties": {
                            "user_id": {"bsonType": "objectId"},
                            "full_name": {"bsonType": "string"},
                            "email": {"bsonType": "string"},
                            "phone": {"bsonType": ["string", "null"]},
                            "address": {"bsonType": ["string", "null"]},
                            "city": {"bsonType": ["string", "null"]},
                            "state": {"bsonType": ["string", "null"]},
                            "zip_code": {"bsonType": ["string", "null"]},
                            "country": {"bsonType": ["string", "null"]},
                            "linkedin": {"bsonType": ["string", "null"]},
                            "github": {"bsonType": ["string", "null"]},
                            "website": {"bsonType": ["string", "null"]},
                            "signature": {"bsonType": ["binData", "null"]},
                            "life_story": {"bsonType": ["string", "null"]},
                            "preferences": {"bsonType": "object"},
                            "created_at": {"bsonType": "date"},
                            "updated_at": {"bsonType": "date"},
                        },
                    }
                },
            }
        )

    def downgrade(self) -> None:
        """Revert the migration."""
        # This migration doesn't need to be reverted
        pass
