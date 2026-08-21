"""Focused tests for the Firebase-retirement persistence foundation."""

from datetime import UTC, datetime, timedelta
from importlib import import_module
from pathlib import Path
from uuid import uuid4

import mongomock
import pytest
from beanie import PydanticObjectId
from pydantic import ValidationError
from pymongo.errors import DuplicateKeyError

from config.settings import ENV_FILES, AuthSettings, FeatureSettings
from core.auth.types import AuthMigrationState, IdentityProvider
from core.models.auth_identity import AuthIdentity
from core.models.oauth_nonce import OAuthNonce
from core.models.refresh_token_session import (
    RefreshTokenDeviceMetadata,
    RefreshTokenSession,
)
from core.models.user import User
from core.services.refresh_token_service import (
    ExpiredRefreshTokenError,
    RefreshTokenReuseError,
    RefreshTokenService,
    RevokedRefreshTokenError,
)
from core.utils.refresh_token import hash_refresh_token


@pytest.mark.asyncio
async def test_auth_models_validate_provider_and_hash_shapes(beanie_db) -> None:
    user_id = PydanticObjectId()
    identity = AuthIdentity(
        user_id=user_id,
        provider=IdentityProvider.GOOGLE,
        provider_subject="google-subject",
    )
    assert identity.provider is IdentityProvider.GOOGLE

    with pytest.raises(ValidationError):
        AuthIdentity(
            user_id=user_id,
            provider="unsupported",
            provider_subject="subject",
        )

    with pytest.raises(ValidationError):
        RefreshTokenSession(
            user_id=user_id,
            family_id=str(uuid4()),
            token_hash="plaintext-token",
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )


@pytest.mark.asyncio
async def test_existing_firebase_user_loads_without_new_fields_or_backfill(
    beanie_db,
) -> None:
    user_id = PydanticObjectId()
    legacy_document = {
        "_id": user_id,
        "username": "legacy-user",
        "email": "legacy@example.com",
        "firebase_uid": "firebase-legacy-uid",
        "auth_provider": "firebase.password",
    }
    collection = beanie_db["test_db"]["users"]
    await collection.insert_one(legacy_document)

    user = await User.get(user_id)
    assert user is not None
    assert user.firebase_uid == "firebase-legacy-uid"
    assert user.password_hash is None
    assert user.auth_migration_state is AuthMigrationState.FIREBASE_ONLY

    stored = await collection.find_one({"_id": user_id})
    assert "password_hash" not in stored
    assert "auth_migration_state" not in stored


@pytest.mark.asyncio
async def test_native_user_without_firebase_uid_validates_and_persists(
    beanie_db,
) -> None:
    native_user = User(
        username="native-user",
        email="native@example.com",
        auth_provider="password",
        password_hash="native-password-hash",
        auth_migration_state=AuthMigrationState.NATIVE,
    )
    await native_user.insert()

    stored_user = await User.get(native_user.id)
    assert stored_user is not None
    assert stored_user.firebase_uid is None
    assert stored_user.password_hash == "native-password-hash"
    assert stored_user.auth_migration_state is AuthMigrationState.NATIVE


@pytest.mark.asyncio
async def test_refresh_token_creation_hashes_plaintext_at_rest(
    beanie_db,
    test_user: User,
) -> None:
    service = RefreshTokenService(token_lifetime=timedelta(days=7))
    issued = await service.create_session(
        user_id=test_user.id,
        device=RefreshTokenDeviceMetadata(
            device_name="Test browser",
            user_agent="pytest",
        ),
    )
    raw_token = issued.token.get_secret_value()

    stored = await beanie_db["test_db"]["refresh_token_sessions"].find_one(
        {"_id": issued.session.id}
    )
    assert stored["token_hash"] == hash_refresh_token(raw_token)
    assert raw_token not in repr(stored)
    assert stored["device"]["device_name"] == "Test browser"


@pytest.mark.asyncio
async def test_refresh_token_rotation_replaces_hash_atomically(
    beanie_db,
    test_user: User,
) -> None:
    service = RefreshTokenService(token_lifetime=timedelta(days=7))
    issued_at = datetime.now(UTC).replace(microsecond=0)
    issued = await service.create_session(user_id=test_user.id, now=issued_at)
    original = issued.token.get_secret_value()

    rotated = await service.rotate(original, now=issued_at + timedelta(days=1))
    replacement = rotated.token.get_secret_value()
    stored = await RefreshTokenSession.get(issued.session.id)

    assert stored is not None
    assert replacement != original
    assert stored.token_hash == hash_refresh_token(replacement)
    assert stored.used_token_hashes == [hash_refresh_token(original)]
    assert stored.rotation_count == 1
    assert stored.expires_at.replace(tzinfo=UTC) == issued_at + timedelta(days=7)
    assert original not in repr(
        await beanie_db["test_db"]["refresh_token_sessions"].find_one(
            {"_id": issued.session.id}
        )
    )


@pytest.mark.asyncio
async def test_reused_token_revokes_family_and_blocks_current_token(
    beanie_db,
    test_user: User,
) -> None:
    service = RefreshTokenService(token_lifetime=timedelta(days=7))
    issued = await service.create_session(user_id=test_user.id)
    original = issued.token.get_secret_value()
    rotated = await service.rotate(original)

    with pytest.raises(RefreshTokenReuseError):
        await service.rotate(original)

    stored = await RefreshTokenSession.get(issued.session.id)
    assert stored is not None
    assert stored.revoked_at is not None
    assert stored.reuse_detected_at is not None
    assert stored.revocation_reason == "refresh_token_reuse"

    with pytest.raises(RevokedRefreshTokenError):
        await service.rotate(rotated.token.get_secret_value())


@pytest.mark.asyncio
async def test_explicit_family_and_user_revocation(
    beanie_db,
    test_user: User,
) -> None:
    service = RefreshTokenService(token_lifetime=timedelta(days=7))
    first = await service.create_session(user_id=test_user.id)
    second = await service.create_session(user_id=test_user.id)

    revoked = await service.revoke_family(family_id=first.session.family_id)
    assert revoked is not None
    assert revoked.revocation_reason == "user_revoked"

    revoked_count = await service.revoke_all_for_user(user_id=test_user.id)
    assert revoked_count == 1
    refreshed_second = await RefreshTokenSession.get(second.session.id)
    assert refreshed_second is not None
    assert refreshed_second.revocation_reason == "user_revoked_all"


@pytest.mark.asyncio
async def test_expired_refresh_token_cannot_rotate(
    beanie_db,
    test_user: User,
) -> None:
    service = RefreshTokenService(token_lifetime=timedelta(days=7))
    now = datetime.now(UTC)
    issued = await service.create_session(user_id=test_user.id, now=now)

    with pytest.raises(ExpiredRefreshTokenError):
        await service.rotate(
            issued.token.get_secret_value(),
            now=now + timedelta(days=8),
        )


def test_auth_configuration_preserves_firebase_compatibility_defaults() -> None:
    assert FeatureSettings.model_fields["enable_firebase_auth"].default is True
    assert FeatureSettings.model_fields["enable_native_auth"].default is False
    assert AuthSettings.model_fields["jwt_access_token_expire_minutes"].default == 1440
    assert (
        AuthSettings.model_fields["jwt_native_access_token_expire_minutes"].default
        == 15
    )
    assert AuthSettings.model_fields["jwt_refresh_token_expire_days"].default == 30
    assert (
        AuthSettings.model_fields["password_reset_token_expire_minutes"].default == 60
    )
    assert (
        AuthSettings.model_fields["email_verification_token_expire_minutes"].default
        == 1440
    )
    assert AuthSettings.model_fields["refresh_cookie_secure"].default is True
    assert AuthSettings.model_fields["refresh_cookie_samesite"].default == "lax"
    assert AuthSettings.model_fields["refresh_cookie_path"].default == (
        "/api/v1/auth/password"
    )
    assert AuthSettings.model_fields["oauth_jwks_cache_ttl_seconds"].default == 3600
    assert AuthSettings.model_fields["oauth_nonce_cookie_secure"].default is True
    assert AuthSettings.model_fields["oauth_nonce_cookie_samesite"].default == "lax"
    assert AuthSettings.model_fields["oauth_nonce_cookie_path"].default == (
        "/api/v1/auth/oauth"
    )
    assert (
        AuthSettings.model_fields["oauth_nonce_cookie_max_age_seconds"].default == 600
    )
    assert AuthSettings.model_fields["oauth_google_web_audiences"].default == ""
    assert AuthSettings.model_config["env_file"] == ENV_FILES
    assert all(Path(env_file).is_absolute() for env_file in ENV_FILES)
    configured_oauth = AuthSettings(
        OAUTH_GOOGLE_WEB_AUDIENCES="web-a, web-b",
        OAUTH_GOOGLE_IOS_AUDIENCES="ios-a",
        OAUTH_GOOGLE_ANDROID_AUDIENCES="android-a",
        OAUTH_APPLE_AUDIENCES="com.yarba.app, com.yarba.web",
        _env_file=None,
    )
    assert configured_oauth.google_oauth_audience_allowlist == frozenset(
        {"web-a", "web-b", "ios-a", "android-a"}
    )
    assert configured_oauth.apple_oauth_audience_allowlist == frozenset(
        {"com.yarba.app", "com.yarba.web"}
    )
    local_cookie_settings = AuthSettings.model_validate(
        {
            "REFRESH_COOKIE_SECURE": False,
            "REFRESH_COOKIE_SAMESITE": "lax",
            "OAUTH_NONCE_COOKIE_SECURE": False,
        }
    )
    assert local_cookie_settings.refresh_cookie_secure is False
    assert local_cookie_settings.refresh_cookie_samesite == "lax"
    assert local_cookie_settings.oauth_nonce_cookie_secure is False
    with pytest.raises(ValidationError):
        AuthSettings.model_validate(
            {
                "REFRESH_COOKIE_SECURE": False,
                "REFRESH_COOKIE_SAMESITE": "none",
            }
        )
    with pytest.raises(ValidationError):
        AuthSettings(
            OAUTH_NONCE_COOKIE_PATH="/",
            _env_file=None,
        )
    with pytest.raises(ValidationError):
        AuthSettings(
            OAUTH_NONCE_COOKIE_MAX_AGE_SECONDS=601,
            _env_file=None,
        )

    enabled_native = FeatureSettings(
        ENABLE_FIREBASE_AUTH=False,
        ENABLE_NATIVE_AUTH=True,
        _env_file=None,
    )
    assert enabled_native.enable_firebase_auth is False
    assert enabled_native.enable_native_auth is True


def test_auth_migration_keeps_users_unchanged_and_creates_unique_indexes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration_module = import_module(
        "core.database.migrations.20260812000000_auth_persistence_foundation"
    )
    client = mongomock.MongoClient()
    db = client["auth_foundation_test"]
    legacy_user = {
        "_id": PydanticObjectId(),
        "username": "legacy",
        "email": "legacy@example.com",
        "firebase_uid": "firebase-uid",
    }
    db.users.insert_one(legacy_user)
    validators: dict[str, dict[str, object]] = {}

    def capture_validator(database, collection, validator, **kwargs) -> None:
        validators[collection] = validator

    monkeypatch.setattr(migration_module, "ensure_validator", capture_validator)
    migration = migration_module.AuthPersistenceFoundationMigration(db)
    migration.upgrade()

    assert db.users.find_one({"_id": legacy_user["_id"]}) == legacy_user
    user_schema = validators["users"]["$jsonSchema"]
    assert "firebase_uid" not in user_schema["required"]
    assert "password_hash" not in user_schema["required"]
    assert "auth_migration_state" not in user_schema["required"]
    assert user_schema["properties"]["firebase_uid"]["bsonType"] == ["string", "null"]

    identity_indexes = list(db.auth_identities.list_indexes())
    assert any(
        list(index["key"].items()) == [("provider", 1), ("provider_subject", 1)]
        and index.get("unique") is True
        for index in identity_indexes
    )
    identity_document = {
        "user_id": PydanticObjectId(),
        "provider": "google",
        "provider_subject": "unique-subject",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    db.auth_identities.insert_one(identity_document)
    with pytest.raises(DuplicateKeyError):
        db.auth_identities.insert_one(
            {
                **identity_document,
                "_id": PydanticObjectId(),
                "user_id": PydanticObjectId(),
            }
        )

    session_indexes = list(db.refresh_token_sessions.list_indexes())
    assert any(
        list(index["key"].items()) == [("token_hash", 1)]
        and index.get("unique") is True
        for index in session_indexes
    )
    assert any(
        list(index["key"].items()) == [("family_id", 1)] and index.get("unique") is True
        for index in session_indexes
    )
    assert any(
        list(index["key"].items()) == [("expires_at", 1)]
        and index.get("expireAfterSeconds") == 0
        for index in session_indexes
    )
    assert any(
        list(index.document["key"].items()) == [("expires_at", 1)]
        and index.document.get("expireAfterSeconds") == 0
        for index in RefreshTokenSession.Settings.indexes
    )
    action_indexes = list(db.auth_action_tokens.list_indexes())
    assert any(
        list(index["key"].items()) == [("token_hash", 1)]
        and index.get("unique") is True
        for index in action_indexes
    )
    nonce_indexes = list(db.oauth_nonces.list_indexes())
    assert any(
        list(index["key"].items()) == [("cookie_hash", 1)]
        and index.get("unique") is True
        for index in nonce_indexes
    )
    assert any(
        list(index["key"].items()) == [("expires_at", 1)]
        and index.get("expireAfterSeconds") == 0
        for index in nonce_indexes
    )
    assert any(
        list(index.document["key"].items()) == [("expires_at", 1)]
        and index.document.get("expireAfterSeconds") == 0
        for index in OAuthNonce.Settings.indexes
    )
    assert any(
        list(index["key"].items()) == [("expires_at", 1)]
        and index.get("expireAfterSeconds") == 0
        for index in action_indexes
    )
