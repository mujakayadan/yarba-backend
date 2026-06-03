"""
Initial schema setup for RBT database

Migration created at: 2024-06-20T00:00:00
"""

from core.database.migrations.migration_manager import Migration


class InitialSchemaMigration(Migration):
    """
    Initial schema setup for RBT database
    """

    def upgrade(self) -> None:
        """Apply the migration."""
        # Create collections with validators

        # Users collection
        self.db.create_collection("users")
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
                            "last_login": {"bsonType": "date"},
                            "login_attempts": {"bsonType": "int"},
                            "account_locked_until": {"bsonType": "date"},
                            "reset_password_token": {"bsonType": "string"},
                            "reset_password_expires": {"bsonType": "date"},
                            "verification_token": {"bsonType": "string"},
                            "subscription_status": {"bsonType": "string"},
                            "subscription_expires": {"bsonType": "date"},
                            "last_active": {"bsonType": "date"},
                            "created_at": {"bsonType": "date"},
                            "updated_at": {"bsonType": "date"},
                        },
                    }
                },
            }
        )

        # Profiles collection
        self.db.create_collection("profiles")
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
                            "phone": {"bsonType": "string"},
                            "address": {"bsonType": "string"},
                            "city": {"bsonType": "string"},
                            "state": {"bsonType": "string"},
                            "zip_code": {"bsonType": "string"},
                            "country": {"bsonType": "string"},
                            "linkedin": {"bsonType": "string"},
                            "github": {"bsonType": "string"},
                            "website": {"bsonType": "string"},
                            "signature": {"bsonType": "binData"},
                            "life_story": {"bsonType": "string"},
                            "preferences": {"bsonType": "object"},
                            "created_at": {"bsonType": "date"},
                            "updated_at": {"bsonType": "date"},
                        },
                    }
                },
            }
        )

        # Portfolios collection
        self.db.create_collection("portfolios")
        self.db.command(
            {
                "collMod": "portfolios",
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["user_id", "title"],
                        "properties": {
                            "user_id": {"bsonType": "objectId"},
                            "title": {"bsonType": "string"},
                            "description": {"bsonType": "string"},
                            "professional_title": {"bsonType": "string"},
                            "career_summary": {"bsonType": "object"},
                            "skills": {"bsonType": "array"},
                            "work_experience": {"bsonType": "array"},
                            "education": {"bsonType": "array"},
                            "projects": {"bsonType": "array"},
                            "theme": {"bsonType": "string"},
                            "layout": {"bsonType": "string"},
                            "items_per_page": {"bsonType": "int"},
                            "custom_sections": {"bsonType": "object"},
                            "is_active": {"bsonType": "bool"},
                            "is_public": {"bsonType": "bool"},
                            "password_protected": {"bsonType": "bool"},
                            "access_password": {"bsonType": "string"},
                            "created_at": {"bsonType": "date"},
                            "updated_at": {"bsonType": "date"},
                            "last_published": {"bsonType": "date"},
                        },
                    }
                },
            }
        )

        # Portfolio items collection
        self.db.create_collection("portfolio_items")
        self.db.command(
            {
                "collMod": "portfolio_items",
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["portfolio_id", "title", "type"],
                        "properties": {
                            "portfolio_id": {"bsonType": "objectId"},
                            "title": {"bsonType": "string"},
                            "description": {"bsonType": "string"},
                            "type": {"bsonType": "string"},
                            "url": {"bsonType": "string"},
                            "image_url": {"bsonType": "string"},
                            "technologies": {"bsonType": "array"},
                            "tags": {"bsonType": "array"},
                            "date": {"bsonType": "string"},
                            "highlights": {"bsonType": "array"},
                            "order": {"bsonType": "int"},
                            "is_featured": {"bsonType": "bool"},
                            "metadata": {"bsonType": "object"},
                            "created_at": {"bsonType": "date"},
                            "updated_at": {"bsonType": "date"},
                        },
                    }
                },
            }
        )

        # Resumes collection
        self.db.create_collection("resumes")
        self.db.command(
            {
                "collMod": "resumes",
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["user_id", "profile_id", "portfolio_id"],
                        "properties": {
                            "user_id": {"bsonType": "objectId"},
                            "profile_id": {"bsonType": "objectId"},
                            "portfolio_id": {"bsonType": "objectId"},
                            "title": {"bsonType": "string"},
                            "template_id": {"bsonType": "string"},
                            "company_name": {"bsonType": "string"},
                            "job_title": {"bsonType": "string"},
                            "job_description": {"bsonType": "string"},
                            "content": {"bsonType": "object"},
                            "custom_sections": {"bsonType": "array"},
                            "resume_pdf_key": {"bsonType": "string"},
                            "created_at": {"bsonType": "date"},
                            "updated_at": {"bsonType": "date"},
                        },
                    }
                },
            }
        )

        # Create indexes
        self.db.users.create_index("username", unique=True)
        self.db.users.create_index("email", unique=True)

        self.db.profiles.create_index("user_id")
        self.db.profiles.create_index("email")

        self.db.portfolios.create_index("user_id")
        self.db.portfolios.create_index("is_public")

        self.db.portfolio_items.create_index("portfolio_id")
        self.db.portfolio_items.create_index("type")
        self.db.portfolio_items.create_index("is_featured")

        self.db.resumes.create_index("user_id")
        self.db.resumes.create_index("profile_id")
        self.db.resumes.create_index("portfolio_id")

    def downgrade(self) -> None:
        """Revert the migration."""
        # Drop all collections
        self.db.users.drop()
        self.db.profiles.drop()
        self.db.portfolios.drop()
        self.db.portfolio_items.drop()
        self.db.resumes.drop()
