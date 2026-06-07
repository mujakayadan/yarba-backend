"""
Update users collection validator for Firebase authentication.

Migration created at: 2025-06-07T00:00:00
"""

from pymongo.errors import OperationFailure

from core.database.migrations.migration_manager import Migration


class FirebaseUserValidatorMigration(Migration):
    """Align users collection validator with Firebase-authenticated User model."""

    def upgrade(self) -> None:
        validator = {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["username", "email", "firebase_uid"],
                "properties": {
                    "username": {"bsonType": "string"},
                    "email": {"bsonType": "string"},
                    "firebase_uid": {"bsonType": "string"},
                    "auth_provider": {"bsonType": "string"},
                    "is_active": {"bsonType": "bool"},
                    "is_superuser": {"bsonType": "bool"},
                    "email_verified": {"bsonType": "bool"},
                    "is_new_user": {"bsonType": "bool"},
                    "current_setup_step": {"bsonType": "int"},
                    "last_login": {"bsonType": ["date", "null"]},
                    "subscription_status": {"bsonType": "string"},
                    "subscription_expires": {"bsonType": ["date", "null"]},
                    "linkedin_email": {"bsonType": ["string", "null"]},
                    "linkedin_integration_enabled": {"bsonType": "bool"},
                    "linkedin_last_login": {"bsonType": ["date", "null"]},
                    "linkedin_auth_token": {"bsonType": ["string", "null"]},
                    "last_active": {"bsonType": ["date", "null"]},
                    "created_at": {"bsonType": "date"},
                    "updated_at": {"bsonType": "date"},
                },
            }
        }
        try:
            self.db.command({"collMod": "users", "validator": validator})
        except OperationFailure as exc:
            if exc.code == 8000 and "collMod" in str(exc):
                msg = (
                    "MongoDB user lacks collMod on users. Grant dbAdmin on the "
                    "database (Atlas: Database Access → user → Built-in Role "
                    "dbAdmin@rbt) or set MIGRATIONS_MONGODB_URI to an admin URI "
                    "for the PRE_DEPLOY job."
                )
                raise RuntimeError(msg) from exc
            raise

    def downgrade(self) -> None:
        pass
