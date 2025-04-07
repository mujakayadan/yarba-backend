#!/usr/bin/env python
"""
Test script to generate a Firebase-like token for development testing.

This script generates a JWT token that mimics the format of a Firebase ID token,
which can be used for testing Firebase authentication in development mode.

WARNING: This is for LOCAL DEVELOPMENT TESTING ONLY.
Never use this in production environments!
"""

import argparse
import datetime
import json
import os
import sys
import time
from typing import Any, Dict

try:
    import jwt
except ImportError:
    print("PyJWT module not found. Install it with: pip install pyjwt[crypto]")
    sys.exit(1)

# Default values
DEFAULT_EMAIL = "test@example.com"
DEFAULT_USER_ID = "test-firebase-uid-1234567890"
DEFAULT_EXPIRY = 3600  # 1 hour
DEFAULT_SECRET = "dev-testing-secret-key"
DEFAULT_OUTPUT = "token.txt"


def generate_firebase_like_token(
    email: str,
    user_id: str,
    expiry_seconds: int,
    secret: str,
    additional_claims: Dict[str, Any] = None,
) -> str:
    """
    Generate a token that mimics the format of a Firebase ID token.

    Args:
        email: User email
        user_id: User ID (uid)
        expiry_seconds: Token expiration in seconds
        secret: Secret key for signing the token
        additional_claims: Additional claims to include in the token

    Returns:
        str: JWT token
    """
    now = int(time.time())

    # Basic claims that mimic Firebase token structure
    payload = {
        "iss": "https://securetoken.google.com/test-project",
        "aud": "test-project",
        "auth_time": now,
        "user_id": user_id,
        "sub": user_id,
        "iat": now,
        "exp": now + expiry_seconds,
        "email": email,
        "email_verified": True,
        "uid": user_id,
        "firebase": {"identities": {"email": [email]}, "sign_in_provider": "password"},
        # Special flag to indicate this is a test token
        "test_mode": True,
    }

    # Add any additional claims
    if additional_claims:
        payload.update(additional_claims)

    # Create a JWT with header that mimics Firebase tokens
    token = jwt.encode(
        payload,
        secret,
        algorithm="HS256",
        headers={"kid": "test-key-id-123", "typ": "JWT"},
    )

    return token


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate a Firebase-like JWT token for development testing"
    )
    parser.add_argument(
        "--email",
        default=DEFAULT_EMAIL,
        help=f"User email address (default: {DEFAULT_EMAIL})",
    )
    parser.add_argument(
        "--user-id",
        default=DEFAULT_USER_ID,
        help=f"User ID (default: {DEFAULT_USER_ID})",
    )
    parser.add_argument(
        "--expiry",
        type=int,
        default=DEFAULT_EXPIRY,
        help=f"Token expiration in seconds (default: {DEFAULT_EXPIRY})",
    )
    parser.add_argument(
        "--secret",
        default=DEFAULT_SECRET,
        help=f"Secret key for signing (default: {DEFAULT_SECRET})",
    )
    parser.add_argument("--claims", help="JSON string of additional claims to include")
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Output file for token (default: {DEFAULT_OUTPUT})",
    )

    args = parser.parse_args()

    additional_claims = {}
    if args.claims:
        try:
            additional_claims = json.loads(args.claims)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in claims: {args.claims}")
            sys.exit(1)

    try:
        token = generate_firebase_like_token(
            args.email, args.user_id, args.expiry, args.secret, additional_claims
        )

        print(f"Generated test token for {args.email}")
        print(
            f"Expires: {datetime.datetime.now() + datetime.timedelta(seconds=args.expiry)}"
        )

        # Save to file
        with open(args.output, "w") as f:
            f.write(token)

        print(f"Token saved to {args.output}")
        print("\nToken preview (first 40 chars):")
        print(f"{token[:40]}...")

    except Exception as e:
        print(f"Error generating token: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
