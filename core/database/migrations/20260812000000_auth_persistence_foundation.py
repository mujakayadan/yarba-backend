"""Add identities, refresh sessions, and one-time auth/OAuth token state.

Migration created at: 2026-08-12T00:00:00
"""

from __future__ import annotations

from pymongo import ASCENDING, IndexModel

from core.database.migrations.migration_manager import Migration
from core.database.migrations.schema_helpers import (
    ensure_collection,
    ensure_index_models,
    ensure_validator,
)

_USER_PROPERTIES = {
    "username": {"bsonType": "string"},
    "email": {"bsonType": "string"},
    "firebase_uid": {"bsonType": ["string", "null"]},
    "auth_provider": {"bsonType": "string"},
    "password_hash": {"bsonType": ["string", "null"]},
    "auth_migration_state": {
        "bsonType": "string",
        "enum": ["firebase_only", "dual", "native"],
    },
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
}

_USERS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["username", "email"],
        "properties": _USER_PROPERTIES,
    }
}

_AUTH_IDENTITIES_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "user_id",
            "provider",
            "provider_subject",
            "created_at",
            "updated_at",
        ],
        "properties": {
            "user_id": {"bsonType": "objectId"},
            "provider": {
                "bsonType": "string",
                "enum": ["firebase", "password", "google", "apple"],
            },
            "provider_subject": {"bsonType": "string"},
            "provider_email": {"bsonType": ["string", "null"]},
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
        },
    }
}

_REFRESH_TOKEN_SESSIONS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "user_id",
            "family_id",
            "token_hash",
            "expires_at",
            "created_at",
            "updated_at",
        ],
        "properties": {
            "user_id": {"bsonType": "objectId"},
            "family_id": {"bsonType": "string"},
            "token_hash": {"bsonType": "string"},
            "used_token_hashes": {
                "bsonType": "array",
                "items": {"bsonType": "string"},
            },
            "expires_at": {"bsonType": "date"},
            "device": {"bsonType": ["object", "null"]},
            "rotation_count": {"bsonType": "int", "minimum": 0},
            "last_used_at": {"bsonType": ["date", "null"]},
            "last_rotated_at": {"bsonType": ["date", "null"]},
            "revoked_at": {"bsonType": ["date", "null"]},
            "revocation_reason": {"bsonType": ["string", "null"]},
            "reuse_detected_at": {"bsonType": ["date", "null"]},
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
        },
    }
}

_AUTH_ACTION_TOKENS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "token_hash",
            "purpose",
            "user_id",
            "expires_at",
            "created_at",
        ],
        "properties": {
            "token_hash": {"bsonType": "string"},
            "purpose": {
                "bsonType": "string",
                "enum": ["password_reset", "email_verification"],
            },
            "user_id": {"bsonType": "objectId"},
            "expires_at": {"bsonType": "date"},
            "consumed_at": {"bsonType": ["date", "null"]},
            "created_at": {"bsonType": "date"},
        },
    }
}

_OAUTH_NONCES_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "cookie_hash",
            "nonce_hash",
            "provider",
            "expires_at",
            "created_at",
        ],
        "properties": {
            "cookie_hash": {"bsonType": "string"},
            "nonce_hash": {"bsonType": "string"},
            "provider": {
                "bsonType": "string",
                "enum": ["google", "apple"],
            },
            "expires_at": {"bsonType": "date"},
            "consumed_at": {"bsonType": ["date", "null"]},
            "created_at": {"bsonType": "date"},
        },
    }
}


class AuthPersistenceFoundationMigration(Migration):
    """Add transition-safe auth fields, identities, and refresh sessions."""

    def upgrade(self) -> None:
        users = ensure_collection(self.db, "users")
        ensure_validator(self.db, "users", _USERS_VALIDATOR)
        ensure_index_models(
            users,
            [
                IndexModel([("username", ASCENDING)], unique=True),
                IndexModel([("email", ASCENDING)], unique=True),
                IndexModel([("firebase_uid", ASCENDING)]),
            ],
        )

        identities = ensure_collection(self.db, "auth_identities")
        ensure_validator(self.db, "auth_identities", _AUTH_IDENTITIES_VALIDATOR)
        ensure_index_models(
            identities,
            [
                IndexModel(
                    [("provider", ASCENDING), ("provider_subject", ASCENDING)],
                    unique=True,
                ),
                IndexModel([("user_id", ASCENDING)]),
            ],
        )

        sessions = ensure_collection(self.db, "refresh_token_sessions")
        ensure_validator(
            self.db,
            "refresh_token_sessions",
            _REFRESH_TOKEN_SESSIONS_VALIDATOR,
        )
        ensure_index_models(
            sessions,
            [
                IndexModel([("token_hash", ASCENDING)], unique=True),
                IndexModel([("family_id", ASCENDING)], unique=True),
                IndexModel([("user_id", ASCENDING)]),
                IndexModel([("used_token_hashes", ASCENDING)]),
                IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0),
            ],
        )

        action_tokens = ensure_collection(self.db, "auth_action_tokens")
        ensure_validator(
            self.db,
            "auth_action_tokens",
            _AUTH_ACTION_TOKENS_VALIDATOR,
        )
        ensure_index_models(
            action_tokens,
            [
                IndexModel([("token_hash", ASCENDING)], unique=True),
                IndexModel([("user_id", ASCENDING), ("purpose", ASCENDING)]),
                IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0),
            ],
        )

        oauth_nonces = ensure_collection(self.db, "oauth_nonces")
        ensure_validator(self.db, "oauth_nonces", _OAUTH_NONCES_VALIDATOR)
        ensure_index_models(
            oauth_nonces,
            [
                IndexModel([("cookie_hash", ASCENDING)], unique=True),
                IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0),
                IndexModel([("provider", ASCENDING), ("expires_at", ASCENDING)]),
            ],
        )

    def downgrade(self) -> None:
        for name in (
            "auth_identities",
            "refresh_token_sessions",
            "auth_action_tokens",
            "oauth_nonces",
        ):
            if name in self.db.list_collection_names():
                self.db[name].drop()
