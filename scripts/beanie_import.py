#!/usr/bin/env python
"""
Script to migrate data from legacy JSON files to the new MongoDB database.
"""
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Import environment variables
sys.path.append(str(Path(__file__).parent.parent))
from config.env_config import MONGODB_DATABASE, MONGODB_URI


def load_json_file(filename: str) -> List[Dict[str, Any]]:
    """Load JSON data from a file."""
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


def convert_mongo_date(date_obj):
    """Convert MongoDB date object to Python datetime."""
    if date_obj is None:
        return None
    if isinstance(date_obj, dict) and "$date" in date_obj:
        return datetime.fromisoformat(date_obj["$date"].replace("Z", "+00:00"))
    return date_obj if date_obj else None


def migrate_users(db, users_data: List[Dict[str, Any]]) -> Dict[str, str]:
    """Migrate users from legacy data to new database using direct MongoDB."""
    user_id_map = {}  # Map of old user_id to new user_id

    for user_data in users_data:
        try:
            old_user_id = user_data.get("user_id")
            if not old_user_id:
                logger.warning(f"Skipping user without user_id: {user_data}")
                continue

            # Use user_id as username
            username = old_user_id

            # Check if user already exists
            existing_user = db.users.find_one({"username": username})
            if existing_user:
                logger.info(f"User already exists: {username}")
                user_id_map[old_user_id] = str(existing_user["_id"])
                continue

            # Extract dates
            created_at = convert_mongo_date(
                user_data.get("created_at", datetime.utcnow())
            )
            updated_at = convert_mongo_date(
                user_data.get("updated_at", datetime.utcnow())
            )
            last_login = convert_mongo_date(
                user_data.get("last_login", datetime.utcnow())
            )
            last_active = convert_mongo_date(
                user_data.get("last_active", datetime.utcnow())
            )

            # Set default values for required fields
            account_locked_until = convert_mongo_date(
                user_data.get("account_locked_until", None)
            )
            reset_password_token = user_data.get("reset_password_token", None)
            reset_password_expires = convert_mongo_date(
                user_data.get("reset_password_expires", None)
            )
            verification_token = user_data.get("verification_token", None)
            subscription_status = user_data.get("subscription_status", "free")
            subscription_expires = convert_mongo_date(
                user_data.get("subscription_expires", None)
            )

            # Create user document
            user_dict = {
                "username": username,
                "email": user_data.get("email", ""),
                "hashed_password": user_data.get(
                    "hashed_password",
                    "$2b$12$JHIqIUZyyNPWSu5IRKYR8eTFYc16mY5QYA0bK.sMywlO98Noyt1su",
                ),  # Default password if not provided
                "is_active": user_data.get("is_active", True),
                "is_superuser": user_data.get("is_superuser", False),
                "email_verified": user_data.get("email_verified", False),
                "login_attempts": user_data.get("login_attempts", 0),
                "account_locked_until": account_locked_until,
                "reset_password_token": reset_password_token,
                "reset_password_expires": reset_password_expires,
                "verification_token": verification_token,
                "subscription_status": subscription_status,
                "subscription_expires": subscription_expires,
                "last_active": last_active,
                "created_at": created_at,
                "updated_at": updated_at,
                "last_login": last_login,
            }

            # Insert directly using PyMongo
            result = db.users.insert_one(user_dict)
            logger.info(f"Created user: {username}, ID: {result.inserted_id}")
            user_id_map[old_user_id] = str(result.inserted_id)

        except Exception as e:
            logger.error(f"Error migrating user {old_user_id}: {e}")

    logger.info(f"Migrated {len(user_id_map)} users from user_information.users.json")
    return user_id_map


def migrate_profiles(db, user_id_map):
    """Migrate profiles from the old database to the new one."""
    profiles = load_json_file("user_information.profiles.json")
    if not profiles:
        logger.info("No profiles to migrate")
        return

    logger.info(f"Loaded {len(profiles)} records from user_information.profiles.json")

    for profile in profiles:
        old_user_id = profile.get("user_id")
        if not old_user_id:
            logger.warning(f"Skipping profile without user_id: {profile}")
            continue

        # Get the new user_id from the map
        new_user_id = user_id_map.get(old_user_id)
        if not new_user_id:
            logger.warning(f"Skipping profile with invalid user_id: {old_user_id}")
            continue

        try:
            # Get personal information
            personal_info = profile.get("personal_information", {})

            # Convert preferences to the new format if they exist
            user_preferences = profile.get("preferences", {})

            # Create profile document
            profile_dict = {
                "user_id": ObjectId(new_user_id),
                "full_name": personal_info.get("full_name", ""),
                "email": personal_info.get("email", ""),
                "phone": personal_info.get("phone"),
                "address": personal_info.get("address"),
                "city": personal_info.get("city"),
                "state": personal_info.get("state"),
                "zip_code": personal_info.get("zip_code"),
                "country": personal_info.get("country"),
                "linkedin": personal_info.get("linkedin"),
                "github": personal_info.get("github"),
                "website": personal_info.get("website"),
                "life_story": profile.get("life_story"),
                "created_at": convert_mongo_date(
                    profile.get("created_at", datetime.utcnow())
                ),
                "updated_at": convert_mongo_date(
                    profile.get("updated_at", datetime.utcnow())
                ),
                "preferences": {
                    "project_details": user_preferences.get(
                        "project_details",
                        {"max_projects": 4, "bullet_points_per_project": 3},
                    ),
                    "work_experience_details": user_preferences.get(
                        "work_experience_details",
                        {"max_jobs": 4, "bullet_points_per_job": 3},
                    ),
                    "skills_details": user_preferences.get(
                        "skills_details",
                        {
                            "max_categories": 5,
                            "min_skills_per_category": 3,
                            "max_skills_per_category": 10,
                        },
                    ),
                    "career_summary_details": user_preferences.get(
                        "career_summary_details", {"min_words": 15, "max_words": 25}
                    ),
                    "education_details": user_preferences.get(
                        "education_details", {"max_entries": 3, "max_courses": 4}
                    ),
                    "cover_letter_details": user_preferences.get(
                        "cover_letter_details", {}
                    ),
                    "awards_details": user_preferences.get("awards_details", {}),
                    "publications_details": user_preferences.get(
                        "publications_details", {}
                    ),
                    "feature_preferences": user_preferences.get(
                        "feature_preferences",
                        {
                            "check_clearance": True,
                            "auto_save": True,
                            "dark_mode": False,
                        },
                    ),
                    "notifications": user_preferences.get("notifications", {}),
                    "privacy": user_preferences.get("privacy", {}),
                    "llm_preferences": user_preferences.get(
                        "llm_preferences",
                        {
                            "model_type": "Claude",
                            "model_name": "claude-3-5-sonnet-20240620",
                            "temperature": 0.1,
                        },
                    ),
                    "section_preferences": user_preferences.get(
                        "section_preferences",
                        {
                            "personal_information": "Hardcode",
                            "career_summary": "Process",
                            "skills": "Process",
                            "work_experience": "Process",
                            "education": "Process",
                            "projects": "Process",
                            "awards": "Hardcode",
                            "publications": "Hardcode",
                        },
                    ),
                },
            }

            # Insert directly using PyMongo
            result = db.profiles.insert_one(profile_dict)
            logger.info(
                f"Migrated profile for user {old_user_id} -> {new_user_id}, new id: {result.inserted_id}"
            )
        except Exception as e:
            logger.error(f"Error migrating profile for user {old_user_id}: {e}")


def migrate_portfolio_items(db, user_id_map, portfolio_id_map):
    """Migrate portfolio items from the old database to the new one."""
    portfolio_items = load_json_file("user_information.portfolio_items.json")
    if not portfolio_items:
        logger.info("No portfolio items to migrate")
        return

    logger.info(
        f"Loaded {len(portfolio_items)} records from user_information.portfolio_items.json"
    )

    items_migrated = 0
    for item in portfolio_items:
        portfolio_id = item.get("portfolio_id")
        if not portfolio_id:
            logger.warning(f"Skipping portfolio item without portfolio_id: {item}")
            continue

        # Get the new portfolio_id from the map
        new_portfolio_id = portfolio_id_map.get(portfolio_id)
        if not new_portfolio_id:
            logger.warning(
                f"Skipping portfolio item with invalid portfolio_id: {portfolio_id}"
            )
            continue

        try:
            # Create portfolio item document
            item_dict = {
                "portfolio_id": ObjectId(new_portfolio_id),
                "title": item.get("title", ""),
                "description": item.get("description", ""),
                "type": item.get("type", "project"),
                "url": item.get("url", ""),
                "bullet_points": item.get("bullet_points", []),
                "tags": item.get("tags", []),
                "date": item.get("date", ""),
                "order": item.get("order", 0),
                "created_at": convert_mongo_date(
                    item.get("created_at", datetime.utcnow())
                ),
                "updated_at": convert_mongo_date(
                    item.get("updated_at", datetime.utcnow())
                ),
            }

            # Insert directly using PyMongo
            result = db.portfolio_items.insert_one(item_dict)
            logger.info(
                f"Migrated portfolio item for portfolio {portfolio_id} -> {new_portfolio_id}, new id: {result.inserted_id}"
            )
            items_migrated += 1
        except Exception as e:
            logger.error(
                f"Error migrating portfolio item for portfolio {portfolio_id}: {e}"
            )

    logger.info(f"Migrated {items_migrated} portfolio items")


def migrate_portfolios(db, user_id_map):
    """Migrate portfolios from the old database to the new one."""
    portfolios = load_json_file("user_information.portfolio.json")
    if not portfolios:
        logger.info("No portfolios to migrate")
        return {}

    logger.info(
        f"Loaded {len(portfolios)} records from user_information.portfolio.json"
    )

    portfolio_id_map = {}  # Map of old portfolio_id to new portfolio_id
    for portfolio in portfolios:
        old_user_id = portfolio.get("user_id")
        if not old_user_id:
            logger.warning(f"Skipping portfolio without user_id: {portfolio}")
            continue

        # Get the new user_id from the map
        new_user_id = user_id_map.get(old_user_id)
        if not new_user_id:
            logger.warning(f"Skipping portfolio with invalid user_id: {old_user_id}")
            continue

        try:
            # Extract career summary data
            career_summary_data = portfolio.get("career_summary", {})

            # Create portfolio document
            portfolio_dict = {
                "user_id": ObjectId(new_user_id),
                "profile_id": None,  # Will be updated later if needed
                "title": portfolio.get("name", "Default Portfolio"),
                "description": portfolio.get("description", ""),
                "professional_title": portfolio.get("professional_title", ""),
                "career_summary": {
                    "job_titles": career_summary_data.get("job_titles", []),
                    "years_of_experience": career_summary_data.get(
                        "years_of_experience", ""
                    ),
                    "default_summary": career_summary_data.get("default_summary", ""),
                },
                "skills": portfolio.get("skills", []),
                "work_experience": portfolio.get("work_experience", []),
                "education": portfolio.get("education", []),
                "projects": portfolio.get("projects", []),
                "awards": portfolio.get("awards", []),
                "publications": portfolio.get("publications", []),
                "certifications": portfolio.get("certifications", []),
                "custom_sections": {
                    "enabled": portfolio.get("custom_sections", {}).get("enabled", []),
                    "order": portfolio.get("custom_sections", {}).get("order", []),
                },
                "is_active": portfolio.get("is_active", True),
                "version": portfolio.get("version", "1.0"),
                "created_at": convert_mongo_date(
                    portfolio.get("created_at", datetime.utcnow())
                ),
                "updated_at": convert_mongo_date(
                    portfolio.get("updated_at", datetime.utcnow())
                ),
            }

            # Insert directly using PyMongo
            result = db.portfolios.insert_one(portfolio_dict)
            logger.info(
                f"Migrated portfolio for user {old_user_id} -> {new_user_id}, new id: {result.inserted_id}"
            )

            # Store the mapping of old portfolio ID to new portfolio ID
            old_portfolio_id = (
                str(portfolio.get("_id", {}).get("$oid"))
                if isinstance(portfolio.get("_id"), dict)
                else str(portfolio.get("_id", ""))
            )
            if old_portfolio_id:
                portfolio_id_map[old_portfolio_id] = str(result.inserted_id)

        except Exception as e:
            logger.error(f"Error migrating portfolio for user {old_user_id}: {e}")

    return portfolio_id_map


def main():
    """Main function to run the migration."""
    logger.info("Starting data migration")

    # Initialize database
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DATABASE]
    logger.info(f"Database initialized with database name: {MONGODB_DATABASE}")
    logger.info("Database initialized")

    # Load data
    users_data = load_json_file("user_information.users.json")
    if not users_data:
        logger.error("No users data found")
        return

    logger.info(f"Loaded {len(users_data)} records from user_information.users.json")

    # Migrate users
    user_id_map = migrate_users(db, users_data)
    logger.info(f"Migrated {len(user_id_map)} users")

    # Migrate profiles
    migrate_profiles(db, user_id_map)
    logger.info(f"Migrated profiles")

    # Migrate portfolios
    portfolio_id_map = migrate_portfolios(db, user_id_map)
    logger.info(f"Migrated {len(portfolio_id_map)} portfolios")

    # Migrate portfolio items
    migrate_portfolio_items(db, user_id_map, portfolio_id_map)

    logger.info("Migration completed")


if __name__ == "__main__":
    main()
