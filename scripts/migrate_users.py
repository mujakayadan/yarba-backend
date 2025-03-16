#!/usr/bin/env python
"""
Script to migrate users from legacy JSON files to the new MongoDB database.
"""
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

from beanie import init_beanie
from bson import ObjectId
from dotenv import load_dotenv

# Add parent directory to path to import core modules
sys.path.append(str(Path(__file__).parent.parent))
from core.database.connections.mongo import mongo_manager
from core.models.user import User

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def load_environment() -> Dict[str, str]:
    """Load environment variables from the correct .env file.

    Returns:
        Dict[str, str]: Dictionary containing environment variables
    """
    # First, try to load from resume_builder/.env
    current_dir = Path(__file__).parent.parent
    new_env_path = current_dir / ".env"

    # Then, try to load from root .env if new_env_path doesn't exist
    root_env_path = current_dir.parent / ".env"

    if new_env_path.exists():
        logger.info(f"Loading environment from: {new_env_path}")
        load_dotenv(dotenv_path=new_env_path, override=True)
    elif root_env_path.exists():
        logger.info(f"Loading environment from: {root_env_path}")
        load_dotenv(dotenv_path=root_env_path, override=True)
    else:
        logger.warning("No .env file found!")

    # Get database connection parameters with defaults
    return {
        "MONGODB_URI": os.getenv("MONGODB_URI", "mongodb://localhost:27017/"),
        "MONGODB_DATABASE": os.getenv("MONGODB_DATABASE", "rbt"),
    }


def load_json_file(filename: str) -> list:
    """Load JSON data from a file.

    Args:
        filename (str): Name of the JSON file to load

    Returns:
        list: List of records from the JSON file
    """
    try:
        file_path = os.path.join("my_data", filename)
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return []

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.info(f"Loaded {len(data)} records from {filename}")
            return data
    except Exception as e:
        logger.error(f"Error loading {filename}: {e}")
        return []


def convert_mongo_date(date_obj) -> datetime:
    """Convert MongoDB date object to Python datetime.

    Args:
        date_obj: Date object from MongoDB

    Returns:
        datetime: Converted datetime object
    """
    if date_obj is None:
        return datetime.utcnow()
    if isinstance(date_obj, dict) and "$date" in date_obj:
        return datetime.fromisoformat(date_obj["$date"].replace("Z", "+00:00"))
    return date_obj if isinstance(date_obj, datetime) else datetime.utcnow()


async def migrate_users() -> Dict[str, str]:
    """Migrate users from legacy data to new database.

    Returns:
        Dict[str, str]: Mapping of old user IDs to new user IDs
    """
    # Load environment variables
    env = load_environment()

    # Initialize MongoDB connection using the manager
    mongo_manager.initialize(env["MONGODB_URI"], env["MONGODB_DATABASE"])

    # Initialize Beanie with the managed connection
    await init_beanie(database=mongo_manager.async_db, document_models=[User])
    logger.info(f"Connected to database: {env['MONGODB_DATABASE']}")

    # Load user data
    users_data = load_json_file("user_information.users.json")
    if not users_data:
        logger.error("No users data found")
        return {}

    # Map of old user_id to new user_id
    user_id_map = {}

    # Process each user
    for user_data in users_data:
        try:
            old_user_id = user_data.get("user_id")
            if not old_user_id:
                logger.warning(f"Skipping user without user_id: {user_data}")
                continue

            # Use user_id as username
            username = old_user_id

            # Check if user already exists
            existing_user = await User.find_one(User.username == username)
            if existing_user:
                logger.info(f"User already exists: {username}")
                user_id_map[old_user_id] = str(existing_user.id)
                continue

            # Create a new user using the Beanie model
            new_user = User(
                username=username,
                email=user_data.get("email", ""),
                hashed_password=user_data.get(
                    "hashed_password",
                    "$2b$12$JHIqIUZyyNPWSu5IRKYR8eTFYc16mY5QYA0bK.sMywlO98Noyt1su",
                ),
                is_active=bool(user_data.get("is_active", True)),
                is_superuser=bool(user_data.get("is_superuser", False)),
                email_verified=bool(user_data.get("email_verified", False)),
                last_login=convert_mongo_date(user_data.get("last_login")),
                login_attempts=int(user_data.get("login_attempts", 0)),
                account_locked_until=convert_mongo_date(
                    user_data.get("account_locked_until")
                ),
                reset_password_token=str(user_data.get("reset_password_token", "")),
                reset_password_expires=convert_mongo_date(
                    user_data.get("reset_password_expires")
                ),
                verification_token=str(user_data.get("verification_token", "")),
                subscription_status=str(user_data.get("subscription_status", "free")),
                subscription_expires=convert_mongo_date(
                    user_data.get("subscription_expires")
                ),
                last_active=convert_mongo_date(user_data.get("last_active")),
                created_at=convert_mongo_date(user_data.get("created_at")),
                updated_at=convert_mongo_date(user_data.get("updated_at")),
            )

            # Save the user using Beanie
            await new_user.save()
            logger.info(f"Created user: {username}, ID: {new_user.id}")
            user_id_map[old_user_id] = str(new_user.id)

        except Exception as e:
            logger.error(f"Error migrating user {old_user_id}: {e}")

    # Save the user ID map to a file
    try:
        with open("user_id_map.json", "w") as f:
            json.dump(user_id_map, f, indent=2)
        logger.info(f"Saved user ID map with {len(user_id_map)} mappings")
    except Exception as e:
        logger.error(f"Error saving user ID map: {e}")

    # Close the connection when done
    mongo_manager.close_async_connection()
    logger.info(f"Migrated {len(user_id_map)} users")
    return user_id_map


async def main():
    """Main function to run the migration."""
    try:
        logger.info("Starting user migration")
        await migrate_users()
        logger.info("User migration completed")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
