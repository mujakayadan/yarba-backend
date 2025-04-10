#!/usr/bin/env python
"""Script to check if Firebase credentials are properly loaded."""

import os
import sys
from pathlib import Path

# Add parent directory to path so we can import project modules
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)


def check_firebase_credentials():
    """Check if Firebase credentials are properly loaded."""
    from config.settings import settings

    # Check individual Firebase credential fields
    print("Checking Firebase credentials:")
    print(f"  Project ID: {settings.auth.firebase_project_id}")
    print(f"  Private Key ID: {settings.auth.firebase_private_key_id}")

    # Only show part of the private key for security
    if settings.auth.firebase_private_key:
        lines = settings.auth.firebase_private_key.split("\n")
        if len(lines) > 2:
            # Show first and last line with ... in between
            print(f"  Private Key: {lines[0]}\n    ...\n    {lines[-1]}")
        else:
            # Just show first few characters
            print(f"  Private Key: {settings.auth.firebase_private_key[:20]}...")
    else:
        print("  Private Key: None")

    print(f"  Client Email: {settings.auth.firebase_client_email}")

    # Check if we can get the credentials dictionary
    creds_dict = settings.auth.get_firebase_credentials_dict()
    print(f"\nCredentials dictionary has {len(creds_dict)} fields")

    if creds_dict:
        print("Firebase credentials are properly loaded and should work.")
    else:
        print("ERROR: Firebase credentials are not properly loaded.")
        print(
            "Check your .env.local file and make sure the base64 encoded private key is valid."
        )


if __name__ == "__main__":
    check_firebase_credentials()
