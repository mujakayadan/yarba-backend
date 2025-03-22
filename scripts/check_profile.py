#!/usr/bin/env python3
"""Script to check a user's profile in the database."""

import asyncio
import sys
from typing import Any, Dict, Optional

from bson import ObjectId
from pymongo import MongoClient

from config.logging_config import get_logger
from config.settings import Settings

logger = get_logger(__name__)
settings = Settings()


async def get_profile_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Get a user's profile by email.

    Args:
        email: User email address

    Returns:
        Optional[Dict[str, Any]]: Profile document if found, None otherwise
    """
    # Get MongoDB URI and database name from settings
    mongo_uri = settings.mongodb_uri
    database_name = settings.mongodb_database

    logger.info(f"Connecting to MongoDB at {mongo_uri}, database: {database_name}")

    # Connect to MongoDB
    client = MongoClient(mongo_uri)
    db = client[database_name]

    # Get user by email
    user = db.users.find_one({"email": email})
    if not user:
        logger.warning(f"User with email {email} not found")
        return None

    logger.info(f"User found: {user['_id']} (username: {user.get('username')})")

    # Get profile for user ID
    profile = db.profiles.find_one({"user_id": user["_id"]})

    # If not found by user_id, try by email as fallback
    if not profile:
        logger.warning(f"Profile for user ID {user['_id']} not found, trying by email")
        profile = db.profiles.find_one({"email": email})

    if not profile:
        logger.warning(f"Profile for user with email {email} not found")
        return None

    logger.info(f"Profile found: {profile['_id']} (user_id: {profile.get('user_id')})")

    return {
        "user": {
            "id": str(user["_id"]),
            "username": user.get("username"),
            "email": user.get("email"),
            "is_active": user.get("is_active"),
        },
        "profile": {
            "id": str(profile["_id"]),
            "user_id": str(profile.get("user_id", "None")),
            "email": profile.get("email"),
            "full_name": profile.get("full_name"),
        },
    }


async def fix_profile_user_id(email: str) -> bool:
    """
    Fix the user_id in a profile for a user with the given email.

    Args:
        email: User email address

    Returns:
        bool: True if fixed, False otherwise
    """
    # Get MongoDB URI and database name from settings
    mongo_uri = settings.mongodb_uri
    database_name = settings.mongodb_database

    # Connect to MongoDB
    client = MongoClient(mongo_uri)
    db = client[database_name]

    # Get user by email
    user = db.users.find_one({"email": email})
    if not user:
        logger.warning(f"User with email {email} not found")
        return False

    # Get profile by email
    profile = db.profiles.find_one({"email": email})
    if not profile:
        logger.warning(f"Profile with email {email} not found")
        return False

    # Check if user_id needs to be updated
    if profile.get("user_id") != user["_id"]:
        logger.info(
            f"Updating profile {profile['_id']} user_id from {profile.get('user_id')} to {user['_id']}"
        )

        # Update the profile's user_id
        result = db.profiles.update_one(
            {"_id": profile["_id"]}, {"$set": {"user_id": user["_id"]}}
        )

        if result.modified_count > 0:
            logger.info("Profile updated successfully")
            return True
        else:
            logger.warning("Profile update failed")
            return False
    else:
        logger.info("Profile user_id is already correct")
        return True


async def main() -> None:
    """Main function."""
    if len(sys.argv) < 2:
        logger.error("Usage: python check_profile.py <email> [--fix]")
        sys.exit(1)

    email = sys.argv[1]
    should_fix = "--fix" in sys.argv

    result = await get_profile_by_email(email)

    if result:
        print("\nUser and Profile Information:")
        print(f"User ID:     {result['user']['id']}")
        print(f"Username:    {result['user']['username']}")
        print(f"User Email:  {result['user']['email']}")
        print(f"Is Active:   {result['user']['is_active']}")
        print("\nProfile Information:")
        print(f"Profile ID:  {result['profile']['id']}")
        print(f"Profile User ID: {result['profile']['user_id']}")
        print(f"Profile Email:   {result['profile']['email']}")
        print(f"Full Name:       {result['profile']['full_name']}")

        # Check mismatch
        if result["user"]["id"] != result["profile"]["user_id"]:
            print("\n⚠️ MISMATCH DETECTED: User ID and Profile's user_id do not match!")

            if should_fix:
                print("\nAttempting to fix the mismatch...")
                if await fix_profile_user_id(email):
                    print("✅ Profile fixed successfully!")
                else:
                    print("❌ Failed to fix profile.")
            else:
                print(
                    "Run with --fix flag to update the profile with the correct user_id"
                )
    else:
        print("No data found")


if __name__ == "__main__":
    asyncio.run(main())
