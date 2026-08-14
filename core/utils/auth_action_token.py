"""Opaque authentication action-token helpers."""

import hashlib
import secrets

AUTH_ACTION_TOKEN_PREFIX = "yarba_action_"


def generate_auth_action_token() -> str:
    """Generate a high-entropy action token."""
    return f"{AUTH_ACTION_TOKEN_PREFIX}{secrets.token_urlsafe(48)}"


def hash_auth_action_token(raw_token: str) -> str:
    """Hash an action token for storage and lookup."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
