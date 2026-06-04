"""Tests for Svix webhook verification."""

import base64
import hashlib
import hmac
import json

import pytest

from core.utils.svix_verify import WebhookVerificationError, verify_svix_webhook


def _sign_payload(payload: dict, secret: str) -> tuple[bytes, dict[str, str]]:
    raw_secret = secret[6:] if secret.startswith("whsec_") else secret
    secret_bytes = base64.b64decode(raw_secret)
    body = json.dumps(payload)
    msg_id = "msg_test123"
    timestamp = "1614265330"
    signed = f"{msg_id}.{timestamp}.{body}"
    signature = base64.b64encode(
        hmac.new(secret_bytes, signed.encode(), hashlib.sha256).digest()
    ).decode()
    headers = {
        "svix-id": msg_id,
        "svix-timestamp": timestamp,
        "svix-signature": f"v1,{signature}",
    }
    return body.encode(), headers


def test_verify_svix_webhook_valid():
    secret = base64.b64encode(b"test-secret-key-32bytes-long!!").decode()
    whsec = f"whsec_{secret}"
    payload = {"type": "email.received", "data": {"email_id": "abc"}}
    body, headers = _sign_payload(payload, whsec)
    result = verify_svix_webhook(body, headers, whsec)
    assert result["type"] == "email.received"


def test_verify_svix_webhook_invalid_signature():
    secret = base64.b64encode(b"test-secret-key-32bytes-long!!").decode()
    whsec = f"whsec_{secret}"
    payload = {"type": "email.received", "data": {"email_id": "abc"}}
    body, headers = _sign_payload(payload, whsec)
    headers["svix-signature"] = "v1,invalidsignature="
    with pytest.raises(WebhookVerificationError):
        verify_svix_webhook(body, headers, whsec)
