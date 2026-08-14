"""Shared authentication domain types."""

from enum import StrEnum


class AuthMigrationState(StrEnum):
    """User migration state while Firebase and native auth coexist."""

    FIREBASE_ONLY = "firebase_only"
    DUAL = "dual"
    NATIVE = "native"


class IdentityProvider(StrEnum):
    """Identity providers supported by the auth persistence layer."""

    FIREBASE = "firebase"
    PASSWORD = "password"
    GOOGLE = "google"
    APPLE = "apple"
