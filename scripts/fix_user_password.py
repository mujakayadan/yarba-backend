#!/usr/bin/env python
"""Utility script to fix a user's password directly in MongoDB."""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.logging_config import configure_logging, get_logger
from config.settings import settings
from core.auth.password import get_password_hash
from core.database import get_database, init_db
from core.models.user import User

# Configure logging
configure_logging()
logger = get_logger("fix_user_password")


async def fix_user_password(email_or_username: str, new_password: str):
    """Fix a user's password directly in MongoDB.

    Args:
        email_or_username: User's email or username
        new_password: New password to set
    """
    logger.info(f"Fixing password for user: {email_or_username}")

    # Initialize database
    await init_db()

    # Find user
    user = None
    if "@" in email_or_username:
        # It's an email
        user = await User.find_one({"email": email_or_username})
    else:
        # It's a username
        user = await User.find_one({"username": email_or_username})

    if not user:
        logger.error(f"User not found: {email_or_username}")
        return False

    # Hash the new password
    hashed_password = get_password_hash(new_password)

    # Update the user
    user.hashed_password = hashed_password
    await user.save()

    logger.info(
        f"Password updated successfully for user: {user.username} ({user.email})"
    )
    return True


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Fix a user's password directly in MongoDB"
    )
    parser.add_argument("email_or_username", type=str, help="User's email or username")
    parser.add_argument("new_password", type=str, help="New password to set")

    args = parser.parse_args()

    try:
        success = await fix_user_password(args.email_or_username, args.new_password)
        if success:
            print(
                f"\nPassword updated successfully for user: {args.email_or_username}\n"
            )
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error fixing password: {e}")
        print(f"Error fixing password: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
