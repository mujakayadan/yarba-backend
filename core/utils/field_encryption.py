"""Symmetric field encryption for special-category PII (Fernet)."""

import json
from typing import Any, cast

from cryptography.fernet import Fernet, InvalidToken

from config.settings import settings
from core.exceptions.base import InternalServerException


class FieldEncryptionError(Exception):
    """Raised when encryption is misconfigured or ciphertext is invalid."""


def _require_key() -> str:
    key = settings.auth.application_data_encryption_key.get_secret_value()
    if not key:
        raise FieldEncryptionError(
            "APPLICATION_DATA_ENCRYPTION_KEY is not configured. "
            'Generate with: python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )
    return key


def _cipher() -> Fernet:
    return Fernet(_require_key().encode("utf-8"))


def encrypt_json(data: dict[str, Any]) -> str:
    """Encrypt a JSON-serializable dict for storage."""
    return _cipher().encrypt(json.dumps(data).encode("utf-8")).decode("utf-8")


def decrypt_json(ciphertext: str) -> dict[str, Any]:
    """Decrypt stored ciphertext back to a dict."""
    try:
        raw = _cipher().decrypt(ciphertext.encode("utf-8"))
    except InvalidToken as exc:
        raise InternalServerException("Failed to decrypt stored demographics") from exc
    return cast(dict[str, Any], json.loads(raw.decode("utf-8")))
