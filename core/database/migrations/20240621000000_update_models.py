"""
Update User, Profile, and Portfolio models

Migration created at: 2024-06-21T00:00:00
"""

from pymongo.database import Database
from core.database.migrations.migration_manager import Migration


class UpdateModelsMigration(Migration):
    """
    Update User, Profile, and Portfolio models to:
    1. Remove preference-related classes from User model
    2. Ensure Profile model contains all user preferences
    3. Ensure Portfolio model contains all professional information
    4. Add Preamble and TexHeader collections for LaTeX generation
    """

    def upgrade(self) -> None:
        """Apply the migration."""
        # Update User collection - remove preference fields
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

        # Update Profile collection - ensure it has preferences
        self.db.command(
            {
                "collMod": "profiles",
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["user_id"],
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
                            "preferences": {
                                "bsonType": "object",
                                "properties": {
                                    "project_details": {
                                        "bsonType": "object",
                                        "properties": {
                                            "max_projects": {"bsonType": "int"},
                                            "bullet_points_per_project": {
                                                "bsonType": "int"
                                            },
                                        },
                                    },
                                    "work_experience_details": {
                                        "bsonType": "object",
                                        "properties": {
                                            "max_jobs": {"bsonType": "int"},
                                            "bullet_points_per_job": {
                                                "bsonType": "int"
                                            },
                                        },
                                    },
                                    "skills_details": {
                                        "bsonType": "object",
                                        "properties": {
                                            "max_categories": {"bsonType": "int"},
                                            "min_skills_per_category": {
                                                "bsonType": "int"
                                            },
                                            "max_skills_per_category": {
                                                "bsonType": "int"
                                            },
                                        },
                                    },
                                    "career_summary_details": {
                                        "bsonType": "object",
                                        "properties": {
                                            "min_words": {"bsonType": "int"},
                                            "max_words": {"bsonType": "int"},
                                        },
                                    },
                                    "education_details": {
                                        "bsonType": "object",
                                        "properties": {
                                            "max_entries": {"bsonType": "int"},
                                            "max_courses": {"bsonType": "int"},
                                        },
                                    },
                                    "llm_preferences": {
                                        "bsonType": "object",
                                        "properties": {
                                            "model_type": {"bsonType": "string"},
                                            "model_name": {"bsonType": "string"},
                                            "temperature": {"bsonType": "double"},
                                        },
                                    },
                                },
                            },
                            "created_at": {"bsonType": "date"},
                            "updated_at": {"bsonType": "date"},
                        },
                    }
                },
            }
        )

        # Update Portfolio collection - ensure it has all professional information
        self.db.command(
            {
                "collMod": "portfolios",
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["user_id"],
                        "properties": {
                            "user_id": {"bsonType": "objectId"},
                            "title": {"bsonType": "string"},
                            "description": {"bsonType": "string"},
                            "professional_title": {"bsonType": "string"},
                            "career_summary": {
                                "bsonType": "object",
                                "properties": {
                                    "job_titles": {
                                        "bsonType": "array",
                                        "items": {"bsonType": "string"},
                                    },
                                    "years_of_experience": {"bsonType": "string"},
                                    "default_summary": {"bsonType": "string"},
                                },
                            },
                            "skills": {
                                "bsonType": "array",
                                "items": {
                                    "bsonType": "object",
                                    "properties": {
                                        "category": {"bsonType": "string"},
                                        "skills": {
                                            "bsonType": "array",
                                            "items": {"bsonType": "string"},
                                        },
                                    },
                                },
                            },
                            "work_experience": {
                                "bsonType": "array",
                                "items": {
                                    "bsonType": "object",
                                    "properties": {
                                        "job_title": {"bsonType": "string"},
                                        "company": {"bsonType": "string"},
                                        "location": {"bsonType": "string"},
                                        "time": {"bsonType": "string"},
                                        "responsibilities": {
                                            "bsonType": "array",
                                            "items": {"bsonType": "string"},
                                        },
                                    },
                                },
                            },
                            "education": {
                                "bsonType": "array",
                                "items": {
                                    "bsonType": "object",
                                    "properties": {
                                        "degree_type": {"bsonType": "string"},
                                        "degree": {"bsonType": "string"},
                                        "university_name": {"bsonType": "string"},
                                        "time": {"bsonType": "string"},
                                        "location": {"bsonType": "string"},
                                        "GPA": {"bsonType": "string"},
                                        "transcript": {
                                            "bsonType": "array",
                                            "items": {"bsonType": "string"},
                                        },
                                    },
                                },
                            },
                            "projects": {
                                "bsonType": "array",
                                "items": {
                                    "bsonType": "object",
                                    "properties": {
                                        "name": {"bsonType": "string"},
                                        "bullet_points": {
                                            "bsonType": "array",
                                            "items": {"bsonType": "string"},
                                        },
                                        "date": {"bsonType": "string"},
                                    },
                                },
                            },
                            "awards": {
                                "bsonType": "array",
                                "items": {
                                    "bsonType": "object",
                                    "properties": {
                                        "name": {"bsonType": "string"},
                                        "explanation": {"bsonType": "string"},
                                    },
                                },
                            },
                            "publications": {
                                "bsonType": "array",
                                "items": {
                                    "bsonType": "object",
                                    "properties": {
                                        "name": {"bsonType": "string"},
                                        "publisher": {"bsonType": "string"},
                                        "link": {"bsonType": "string"},
                                        "time": {"bsonType": "string"},
                                    },
                                },
                            },
                            "certifications": {"bsonType": "array"},
                            "custom_sections": {
                                "bsonType": "object",
                                "properties": {
                                    "enabled": {
                                        "bsonType": "array",
                                        "items": {"bsonType": "string"},
                                    },
                                    "order": {
                                        "bsonType": "array",
                                        "items": {"bsonType": "string"},
                                    },
                                },
                            },
                            "is_active": {"bsonType": "bool"},
                            "profile_id": {"bsonType": "objectId"},
                            "version": {"bsonType": "string"},
                            "created_at": {"bsonType": "date"},
                            "updated_at": {"bsonType": "date"},
                        },
                    }
                },
            }
        )

        # Update PortfolioItem collection - simplify based on actual usage
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
                            "bullet_points": {
                                "bsonType": "array",
                                "items": {"bsonType": "string"},
                            },
                            "tags": {
                                "bsonType": "array",
                                "items": {"bsonType": "string"},
                            },
                            "date": {"bsonType": "string"},
                            "order": {"bsonType": "int"},
                            "is_featured": {"bsonType": "bool"},
                            "company": {"bsonType": "string"},
                            "location": {"bsonType": "string"},
                            "created_at": {"bsonType": "date"},
                            "updated_at": {"bsonType": "date"},
                        },
                    }
                },
            }
        )

        # Create or update Preamble collection
        if "preambles" not in self.db.list_collection_names():
            self.db.create_collection("preambles")

        self.db.command(
            {
                "collMod": "preambles",
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["name", "type", "content"],
                        "properties": {
                            "name": {"bsonType": "string"},
                            "type": {"bsonType": "string"},
                            "content": {"bsonType": "string"},
                            "is_default": {"bsonType": "bool"},
                            "created_at": {"bsonType": "date"},
                            "updated_at": {"bsonType": "date"},
                        },
                    }
                },
            }
        )

        # Create or update TexHeader collection
        if "tex_headers" not in self.db.list_collection_names():
            self.db.create_collection("tex_headers")

        self.db.command(
            {
                "collMod": "tex_headers",
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["name", "content"],
                        "properties": {
                            "name": {"bsonType": "string"},
                            "content": {"bsonType": "string"},
                            "category": {"bsonType": "string"},
                            "is_default": {"bsonType": "bool"},
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
        self.db.portfolios.create_index("user_id")
        self.db.portfolio_items.create_index("portfolio_id")
        self.db.portfolio_items.create_index("type")
        self.db.portfolio_items.create_index([("portfolio_id", 1), ("type", 1)])
        self.db.portfolio_items.create_index([("portfolio_id", 1), ("is_featured", 1)])
        self.db.preambles.create_index([("type", 1), ("is_default", 1)])
        self.db.tex_headers.create_index("category")
        self.db.tex_headers.create_index([("name", 1), ("category", 1)])
        self.db.tex_headers.create_index(
            [("name", 1), ("category", 1), ("is_default", 1)]
        )

    def downgrade(self) -> None:
        """Revert the migration."""
        # This is a complex migration that modifies multiple collections
        # For safety, we don't provide an automatic downgrade path
        # To revert, restore from a backup or manually modify the collections
        pass
