#!/usr/bin/env python
"""Utility script to generate password hashes for manual DB updates."""

import argparse
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.auth.password import get_password_hash


def main():
    """Generate a password hash."""
    parser = argparse.ArgumentParser(description="Generate a bcrypt password hash")
    parser.add_argument("password", type=str, help="Password to hash")

    args = parser.parse_args()

    try:
        hashed_password = get_password_hash(args.password)
        print(f"\nPassword Hash: {hashed_password}\n")
        print("You can use this hash to update your user record in MongoDB.")
        print("Example MongoDB update command:")
        print(
            'db.users.updateOne({"email": "your.email@example.com"}, {$set: {"hashed_password": "'
            + hashed_password
            + '"}})'
        )
    except Exception as e:
        print(f"Error generating password hash: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
