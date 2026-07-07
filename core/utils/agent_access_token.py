"""Utilities for agent access token generation and verification."""

import hashlib
import secrets

TOKEN_PREFIX = "yarba_pat_"


def generate_raw_token() -> str:
    """Generate a new raw agent access token."""
    return f"{TOKEN_PREFIX}{secrets.token_urlsafe(32)}"


def hash_token(raw_token: str) -> str:
    """Hash a raw token for storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
