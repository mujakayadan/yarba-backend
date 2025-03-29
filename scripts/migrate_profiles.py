#!/usr/bin/env python
"""
Script to migrate profiles from legacy JSON files to the new MongoDB database.
"""
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from beanie import init_beanie
from bson import ObjectId
from dotenv import load_dotenv
from pydantic import EmailStr

# Add parent directory to path to import core modules
sys.path.append(str(Path(__file__).parent.parent))
from core.database.connections.mongo import mongo_manager
from core.models.profile import Preferences, Profile
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
        "OLD_MONGODB_URI": os.getenv("OLD_MONGODB_URI"),
        "OLD_MONGODB_DATABASE": os.getenv("OLD_MONGODB_DATABASE"),
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


def convert_mongo_date(date_obj) -> Optional[datetime]:
    """Convert MongoDB date object to Python datetime.

    Args:
        date_obj: Date object from MongoDB

    Returns:
        Optional[datetime]: Converted datetime object or None
    """
    if date_obj is None:
        return None
    if isinstance(date_obj, dict) and "$date" in date_obj:
        return datetime.fromisoformat(date_obj["$date"].replace("Z", "+00:00"))
    return date_obj if date_obj else None


def load_user_id_map() -> Dict[str, str]:
    """Load the user ID map from file.

    Returns:
        Dict[str, str]: Mapping of old user IDs to new user IDs
    """
    try:
        with open("user_id_map.json", "r") as f:
            user_id_map = json.load(f)
            logger.info(f"Loaded user ID map with {len(user_id_map)} mappings")
            return user_id_map
    except FileNotFoundError:
        logger.error("User ID map file not found")
        return {}
    except json.JSONDecodeError:
        logger.error("Invalid JSON in user ID map file")
        return {}


def get_default_preferences() -> dict:
    """Get default preferences for a new profile."""
    return {
        "project_details": {"max_projects": 4, "bullet_points_per_project": 3},
        "work_experience_details": {"max_jobs": 4, "bullet_points_per_job": 3},
        "skills_details": {
            "max_categories": 5,
            "min_skills_per_category": 3,
            "max_skills_per_category": 10,
        },
        "career_summary_details": {"min_words": 15, "max_words": 25},
        "education_details": {"max_entries": 3, "max_courses": 4},
        "cover_letter_details": {},
        "awards_details": {},
        "publications_details": {},
        "feature_preferences": {
            "check_clearance": True,
            "auto_save": True,
            "dark_mode": False,
        },
        "notifications": {},
        "privacy": {},
    }


async def migrate_profiles() -> Dict[str, str]:
    """Migrate profiles from legacy data to new database.

    Returns:
        Dict[str, str]: Mapping of old profile IDs to new profile IDs
    """
    # Load environment variables
    env = load_environment()

    # Initialize MongoDB connection using the manager
    mongo_manager.initialize(env["MONGODB_URI"], env["MONGODB_DATABASE"])

    # Initialize Beanie with the managed connection
    await init_beanie(database=mongo_manager.async_db, document_models=[User, Profile])
    logger.info(f"Connected to database: {env['MONGODB_DATABASE']}")

    # Load user ID map
    user_id_map = load_user_id_map()
    if not user_id_map:
        logger.error("No user ID map found, cannot migrate profiles")
        return {}

    # Load profile data
    profiles_data = load_json_file("user_information.profiles.json")
    if not profiles_data:
        logger.error("No profiles data found")
        return {}

    # Map of old profile_id to new profile_id
    profile_id_map = {}

    # Process each profile
    for profile_data in profiles_data:
        try:
            user_id = profile_data.get("user_id")
            if not user_id:
                logger.warning(f"Skipping profile without user_id: {profile_data}")
                continue

            # Check if user exists in the map
            if user_id not in user_id_map:
                logger.warning(f"User ID not found in map: {user_id}")
                continue

            new_user_id = ObjectId(user_id_map[user_id])

            # Check if profile already exists
            existing_profile = await Profile.find_one(Profile.user_id == new_user_id)
            if existing_profile:
                logger.info(f"Profile already exists for user: {user_id}")
                profile_id_map[
                    str(profile_data.get("_id", {}).get("$oid", user_id))
                ] = str(existing_profile.id)
                continue

            # Extract personal information
            personal_information = profile_data.get("personal_information", {})

            # Extract dates
            created_at = convert_mongo_date(profile_data.get("created_at"))
            updated_at = convert_mongo_date(profile_data.get("updated_at"))

            # Create preferences with all required fields
            preferences = Preferences(
                project_details=profile_data.get("preferences", {}).get(
                    "project_details", {}
                ),
                work_experience_details=profile_data.get("preferences", {}).get(
                    "work_experience_details", {}
                ),
                skills_details=profile_data.get("preferences", {}).get(
                    "skills_details", {}
                ),
                career_summary_details=profile_data.get("preferences", {}).get(
                    "career_summary_details", {}
                ),
                education_details=profile_data.get("preferences", {}).get(
                    "education_details", {}
                ),
                cover_letter_details={"paragraphs": 5, "target_age": 25},
                awards_details={"max_awards": 4},
                publications_details={"max_publications": 3},
                feature_preferences=profile_data.get("preferences", {}).get(
                    "feature_preferences", {}
                ),
                notifications=profile_data.get("preferences", {}).get(
                    "notifications", {}
                ),
                privacy=profile_data.get("preferences", {}).get("privacy", {}),
                llm_preferences={
                    "model_type": "Claude",
                    "model_name": "claude-3-5-sonnet-20240620",
                    "temperature": 0.1,
                },
                section_preferences={
                    "personal_information": "Hardcode",
                    "career_summary": "Process",
                    "skills": "Process",
                    "work_experience": "Process",
                    "education": "Process",
                    "projects": "Process",
                    "awards": "Hardcode",
                    "publications": "Hardcode",
                },
            )

            # Create a new profile using the Beanie model
            new_profile = Profile(
                user_id=new_user_id,
                full_name=personal_information.get("full_name", ""),
                email=personal_information.get("email", ""),
                phone=personal_information.get("phone", ""),
                address=personal_information.get("address", ""),
                linkedin=personal_information.get("linkedin", ""),
                github=personal_information.get("github", ""),
                website=personal_information.get("website", ""),
                signature=(
                    profile_data.get("signature", {})
                    .get("image", {})
                    .get("$binary", {})
                    .get("base64", "")
                    .encode()
                    if profile_data.get("signature")
                    else None
                ),
                life_story=profile_data.get("life_story", ""),
                api_keys={},  # Initialize empty API keys dictionary
                preferences=preferences,
                created_at=created_at,
                updated_at=updated_at,
            )

            # Save the profile using Beanie
            await new_profile.save()
            logger.info(f"Created profile for user: {user_id}, ID: {new_profile.id}")
            profile_id_map[str(profile_data.get("_id", {}).get("$oid", user_id))] = str(
                new_profile.id
            )

        except Exception as e:
            logger.error(f"Error migrating profile for user {user_id}: {e}")

    # Save the profile ID map to a file
    try:
        with open("profile_id_map.json", "w") as f:
            json.dump(profile_id_map, f, indent=2)
        logger.info(f"Saved profile ID map with {len(profile_id_map)} mappings")
    except Exception as e:
        logger.error(f"Error saving profile ID map: {e}")

    # Close the connection when done
    mongo_manager.close_async_connection()
    logger.info(f"Migrated {len(profile_id_map)} profiles")
    return profile_id_map


async def main():
    """Main function to run the migration."""
    try:
        logger.info("Starting profile migration")
        await migrate_profiles()
        logger.info("Profile migration completed")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
