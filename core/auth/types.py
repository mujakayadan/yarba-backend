"""Shared authentication domain types."""

from enum import StrEnum


class AuthMigrationState(StrEnum):
    """Stored account authentication mode.

    New accounts are written as NATIVE. FIREBASE_ONLY and DUAL remain valid
    values on existing documents.
    """

    FIREBASE_ONLY = "firebase_only"
    DUAL = "dual"
    NATIVE = "native"


class IdentityProvider(StrEnum):
    """Identity providers stored for an account.

    Application code writes PASSWORD, GOOGLE, and APPLE. FIREBASE is a stored
    value on existing identity rows.
    """

    FIREBASE = "firebase"
    PASSWORD = "password"
    GOOGLE = "google"
    APPLE = "apple"
