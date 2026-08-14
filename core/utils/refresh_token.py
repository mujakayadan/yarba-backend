"""Refresh-token generation and one-way hashing."""

import hashlib
import secrets

REFRESH_TOKEN_PREFIX = "yarba_rt_"


def generate_refresh_token() -> str:
    """Generate a cryptographically random opaque refresh token."""
    return f"{REFRESH_TOKEN_PREFIX}{secrets.token_urlsafe(48)}"


def hash_refresh_token(raw_token: str) -> str:
    """Return the deterministic SHA-256 digest used for token lookup."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
