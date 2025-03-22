"""
Diagnostic script to check MongoDB profile data directly.
"""

import asyncio
import os
import sys
from pathlib import Path

from bson import ObjectId

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from config.logging_config import configure_logging, get_logger
from config.settings import Settings
from core.models.profile import Profile
from core.models.user import User

logger = get_logger(__name__)
configure_logging()


async def init_db():
    """Initialize database connection."""
    settings = Settings()
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_database]

    # Initialize Beanie with the document classes
    await init_beanie(
        database=db,
        document_models=[
            User,
            Profile,
        ],
    )
    return db


async def debug_profile(user_id_str: str):
    """Debug profile for a user ID."""
    try:
        # Connect to database
        db = await init_db()
        print(f"Connected to database: {db.name}")

        # Convert to ObjectId
        try:
            if ObjectId.is_valid(user_id_str):
                user_id = ObjectId(user_id_str)
            else:
                print(f"Invalid ObjectId format: {user_id_str}")
                return
        except Exception as e:
            print(f"Error converting to ObjectId: {e}")
            return

        # First check if the user exists
        user = await User.find_one({"_id": user_id})
        if user:
            print(f"✅ User found: {user.id}, {user.username}")
        else:
            print(f"❌ User not found with ID: {user_id}")

            # Try different user queries
            print("Looking for user with different types...")
            user_by_str = await User.find_one({"_id": user_id_str})
            print(f"User by string ID: {'Found' if user_by_str else 'Not found'}")

            # List all user IDs in the database
            print("\nAll users in database:")
            users = await User.find_all().to_list()
            for u in users:
                print(f"- {u.id}, {u.username}")

        # Try to find the profile directly
        profile = await Profile.find_one({"user_id": user_id})
        if profile:
            print(f"\n✅ Profile found with user_id as ObjectId")
            print(f"Profile ID: {profile.id}")
            print(f"Full name: {profile.full_name}")
            print(f"Email: {profile.email}")
        else:
            print(f"\n❌ Profile not found with user_id as ObjectId")

            # Try with string user_id
            profile_str = await Profile.find_one({"user_id": user_id_str})
            if profile_str:
                print(f"✅ Profile found with user_id as string!")
                print(f"Profile ID: {profile_str.id}")
                print(f"Full name: {profile_str.full_name}")
                print(f"Email: {profile_str.email}")
            else:
                print(f"❌ Profile not found with user_id as string either")

            # List all profiles
            print("\nAll profiles in database:")
            profiles = await Profile.find_all().to_list()
            for p in profiles:
                print(f"- Profile {p.id}, user_id: {p.user_id}, name: {p.full_name}")
                # Check exact type of p.user_id
                print(f"  - Type of user_id: {type(p.user_id)}")

        # Try direct MongoDB query to see raw data
        profiles_collection = db.profiles
        raw_profile = await profiles_collection.find_one({"user_id": user_id})
        if raw_profile:
            print(f"\n✅ Raw profile found with user_id as ObjectId")
            print(f"Raw profile: {raw_profile}")
        else:
            print(f"\n❌ Raw profile not found with user_id as ObjectId")

            # Try string user_id
            raw_profile_str = await profiles_collection.find_one(
                {"user_id": user_id_str}
            )
            if raw_profile_str:
                print(f"✅ Raw profile found with user_id as string!")
                print(f"Raw profile: {raw_profile_str}")
            else:
                print(f"❌ Raw profile not found with user_id as string either")

            # Show all user_id values in profiles collection
            cursor = profiles_collection.find({}, {"user_id": 1})
            print("\nAll user_id values in profiles collection:")
            async for doc in cursor:
                print(f"- {doc.get('user_id')} ({type(doc.get('user_id'))})")

    except Exception as e:
        import traceback

        print(f"Error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    USER_ID = "67d713143f8ee422d6db534a"  # Your test user ID

    if len(sys.argv) > 1:
        USER_ID = sys.argv[1]

    print(f"Debugging profile for user ID: {USER_ID}")
    asyncio.run(debug_profile(USER_ID))
