"""
Current MongoDB schema for Yarba (squashed base migration).

Migration created at: 2025-06-08T00:00:00
"""

from __future__ import annotations

from pymongo import ASCENDING, IndexModel

from core.database.migrations.migration_manager import Migration
from core.database.migrations.schema_helpers import (
    ensure_collection,
    ensure_indexes,
    ensure_validator,
)

_LEGACY_LATEX_COLLECTIONS = ("preambles", "tex_headers")

_USERS_VALIDATOR = {
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

_PROFILES_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["user_id", "personal_information"],
        "properties": {
            "user_id": {"bsonType": "objectId"},
            "personal_information": {"bsonType": "object"},
            "signature_key": {"bsonType": ["string", "null"]},
            "life_story": {"bsonType": ["string", "null"]},
            "profile_picture_key": {"bsonType": ["string", "null"]},
            "api_keys": {"bsonType": "object"},
            "prompt_preferences": {"bsonType": "object"},
            "system_preferences": {"bsonType": "object"},
            "llm_usage": {"bsonType": "object"},
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
        },
    }
}

_PORTFOLIOS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["user_id"],
        "properties": {
            "user_id": {"bsonType": "objectId"},
            "profile_id": {"bsonType": ["objectId", "null"]},
            "career_summary": {"bsonType": "object"},
            "skills": {"bsonType": "array"},
            "work_experience": {"bsonType": "array"},
            "education": {"bsonType": "array"},
            "projects": {"bsonType": "array"},
            "awards": {"bsonType": "array"},
            "publications": {"bsonType": "array"},
            "certifications": {"bsonType": "array"},
            "custom_sections": {"bsonType": "object"},
            "is_active": {"bsonType": "bool"},
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
        },
    }
}

_RESUMES_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["user_id", "profile_id", "portfolio_id"],
        "properties": {
            "user_id": {"bsonType": "objectId"},
            "profile_id": {"bsonType": "objectId"},
            "portfolio_id": {"bsonType": "objectId"},
            "title": {"bsonType": ["string", "null"]},
            "version": {"bsonType": "int"},
            "template_id": {"bsonType": ["string", "null"]},
            "company_name": {"bsonType": ["string", "null"]},
            "job_title": {"bsonType": ["string", "null"]},
            "job_description": {"bsonType": "string"},
            "job_description_url": {"bsonType": ["string", "null"]},
            "content": {"bsonType": "object"},
            "custom_sections": {"bsonType": "array"},
            "resume_pdf_key": {"bsonType": ["string", "null"]},
            "cover_letter_ids": {"bsonType": "array"},
            "llm_settings": {"bsonType": "object"},
            "llm_usage": {"bsonType": "object"},
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
        },
    }
}

_COVER_LETTERS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["user_id", "resume_id"],
        "properties": {
            "user_id": {"bsonType": "objectId"},
            "profile_id": {"bsonType": ["objectId", "null"]},
            "portfolio_id": {"bsonType": ["objectId", "null"]},
            "resume_id": {"bsonType": "objectId"},
            "template_id": {"bsonType": ["string", "null"]},
            "content": {"bsonType": ["string", "null"]},
            "cover_letter_pdf_key": {"bsonType": ["string", "null"]},
            "llm_usage": {"bsonType": "object"},
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
        },
    }
}


class InitialSchemaMigration(Migration):
    """Create collections, validators, and indexes for a fresh Yarba database."""

    def upgrade(self) -> None:
        for legacy in _LEGACY_LATEX_COLLECTIONS:
            if legacy in self.db.list_collection_names():
                self.db[legacy].drop()

        ensure_collection(self.db, "users")
        ensure_validator(self.db, "users", _USERS_VALIDATOR)
        self.db.users.create_indexes(
            [
                IndexModel([("username", ASCENDING)], unique=True),
                IndexModel([("email", ASCENDING)], unique=True),
                IndexModel([("firebase_uid", ASCENDING)]),
            ]
        )

        ensure_collection(self.db, "profiles")
        ensure_validator(self.db, "profiles", _PROFILES_VALIDATOR)
        ensure_indexes(self.db.profiles, ["user_id"])

        ensure_collection(self.db, "portfolios")
        ensure_validator(self.db, "portfolios", _PORTFOLIOS_VALIDATOR)
        ensure_indexes(self.db.portfolios, ["user_id", "profile_id"])

        ensure_collection(self.db, "resumes")
        ensure_validator(self.db, "resumes", _RESUMES_VALIDATOR)
        ensure_indexes(
            self.db.resumes,
            ["user_id", "profile_id", "portfolio_id"],
        )

        ensure_collection(self.db, "cover_letters")
        ensure_validator(self.db, "cover_letters", _COVER_LETTERS_VALIDATOR)
        ensure_indexes(
            self.db.cover_letters,
            ["user_id", "profile_id", "portfolio_id", "resume_id"],
        )

        ensure_collection(self.db, "inbound_emails")
        self.db.inbound_emails.create_indexes(
            [IndexModel([("email_id", ASCENDING)], unique=True)]
        )

        ensure_collection(self.db, "unknown_email_senders")
        self.db.unknown_email_senders.create_indexes(
            [IndexModel([("sender_email", ASCENDING)], unique=True)]
        )

        ensure_collection(self.db, "portfolio_websites")
        self.db.portfolio_websites.create_indexes(
            [
                IndexModel([("user_id", ASCENDING)]),
                IndexModel([("portfolio_id", ASCENDING)]),
                IndexModel([("subdomain", ASCENDING)], unique=True),
                IndexModel([("is_published", ASCENDING)]),
                IndexModel([("user_id", ASCENDING), ("subdomain", ASCENDING)]),
            ]
        )

    def downgrade(self) -> None:
        for name in (
            "users",
            "profiles",
            "portfolios",
            "resumes",
            "cover_letters",
            "inbound_emails",
            "unknown_email_senders",
            "portfolio_websites",
        ):
            if name in self.db.list_collection_names():
                self.db[name].drop()
