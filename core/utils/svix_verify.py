"""Verify Svix-signed webhook payloads (used by Resend)."""

import base64
import hashlib
import hmac
import json
from typing import Any, cast


class WebhookVerificationError(Exception):
    """Raised when webhook signature verification fails."""


def verify_svix_webhook(
    payload: bytes,
    headers: dict[str, str],
    secret: str,
) -> dict[str, Any]:
    """Verify a Svix webhook and return the parsed JSON payload.

    Args:
        payload: Raw request body bytes.
        headers: Request headers (case-insensitive keys supported).
        secret: Webhook signing secret (``whsec_...``).

    Raises:
        WebhookVerificationError: If verification fails.
    """
    normalized = {k.lower(): v for k, v in headers.items()}

    msg_id = normalized.get("svix-id") or normalized.get("webhook-id")
    msg_timestamp = normalized.get("svix-timestamp") or normalized.get(
        "webhook-timestamp"
    )
    msg_signature = normalized.get("svix-signature") or normalized.get(
        "webhook-signature"
    )

    if not msg_id or not msg_timestamp or not msg_signature:
        raise WebhookVerificationError("Missing Svix webhook headers")

    if secret.startswith("whsec_"):
        secret = secret[6:]

    try:
        secret_bytes = base64.b64decode(secret)
    except Exception as exc:
        raise WebhookVerificationError("Invalid webhook secret encoding") from exc

    body = payload.decode("utf-8")
    signed_content = f"{msg_id}.{msg_timestamp}.{body}"
    expected = base64.b64encode(
        hmac.new(
            secret_bytes,
            signed_content.encode("utf-8"),
            hashlib.sha256,
        ).digest()
    ).decode("utf-8")

    verified = False
    for part in msg_signature.split(" "):
        if "," not in part:
            continue
        version, signature = part.split(",", 1)
        if version == "v1" and hmac.compare_digest(expected, signature):
            verified = True
            break

    if not verified:
        raise WebhookVerificationError("Invalid webhook signature")

    return cast(dict[str, Any], json.loads(body))
