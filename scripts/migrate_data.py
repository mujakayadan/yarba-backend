#!/usr/bin/env python
"""
Migration script to populate the new database with data from legacy JSON files.

This script reads the JSON files in the my_data folder and populates the new MongoDB database.
"""

import asyncio
import json
import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from config.logging_config import get_logger
from config.settings import Settings
from core.database import init_db
from core.models.portfolio import CareerSummary, Portfolio
from core.models.profile import Preferences, Profile
from core.models.user import User

# Configure logging to show more details
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = get_logger(__name__)
settings = Settings()

# Path to the data files
DATA_DIR = Path(__file__).parent.parent / "my_data"


async def load_json_file(filename: str) -> List[Dict[str, Any]]:
    """Load data from a JSON file."""
    try:
        file_path = DATA_DIR / filename
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return []

        with open(file_path, "r") as f:
            data = json.load(f)

        logger.info(f"Loaded {len(data)} records from {filename}")
        return data
    except Exception as e:
        logger.error(f"Error loading {filename}: {e}")
        traceback.print_exc()
        return []


async def initialize_database():
    """Initialize the database connection with the correct database name."""
    try:
        # Create a MongoDB client
        client = AsyncIOMotorClient(settings.mongodb_uri)

        # Initialize Beanie with the explicit database name 'rbt'
        await init_beanie(
            database=client.rbt,
            document_models=[
                User,
                Profile,
                Portfolio,
            ],
        )
        logger.info("Database initialized with database name: rbt")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        traceback.print_exc()
        raise


async def migrate_users(users_data: List[Dict[str, Any]]) -> Dict[str, str]:
    """Migrate users from legacy data to new database."""
    user_id_map = {}  # Map of old user_id to new user_id

    for user_data in users_data:
        try:
            old_user_id = user_data.get("user_id")
            if not old_user_id:
                logger.warning(
                    f"Skipping user without user_id: {user_data.get('email')}"
                )
                continue

            logger.debug(f"Processing user: {old_user_id}")

            # Check if user already exists by username
            existing_user = await User.find_one({"username": old_user_id})

            # If not found by username, check by email
            if not existing_user:
                existing_user = await User.find_one({"email": user_data.get("email")})

            if existing_user:
                logger.info(f"User already exists: {old_user_id}")

                # Update existing user with any new data
                existing_user.username = old_user_id
                existing_user.email = user_data.get("email")
                existing_user.hashed_password = user_data.get("hashed_password")
                existing_user.is_active = user_data.get("is_active", True)
                existing_user.is_superuser = user_data.get("is_superuser", False)
                existing_user.email_verified = user_data.get("email_verified", False)
                existing_user.login_attempts = user_data.get("login_attempts", 0)
                existing_user.account_locked_until = user_data.get(
                    "account_locked_until"
                )

                # Only update timestamps if they exist in the data
                if user_data.get("last_login", {}).get("$date"):
                    existing_user.last_login = user_data.get("last_login", {}).get(
                        "$date"
                    )
                if user_data.get("created_at", {}).get("$date"):
                    existing_user.created_at = user_data.get("created_at", {}).get(
                        "$date"
                    )
                if user_data.get("updated_at", {}).get("$date"):
                    existing_user.updated_at = user_data.get("updated_at", {}).get(
                        "$date"
                    )

                await existing_user.save()
                logger.info(f"Updated existing user: {old_user_id}")
                user_id_map[old_user_id] = str(existing_user.id)
                continue

            # Create new user
            logger.debug(f"Creating new user: {old_user_id}")
            new_user = User(
                username=old_user_id,
                email=user_data.get("email"),
                hashed_password=user_data.get("hashed_password"),
                is_active=user_data.get("is_active", True),
                is_superuser=user_data.get("is_superuser", False),
                email_verified=user_data.get("email_verified", False),
                login_attempts=user_data.get("login_attempts", 0),
                account_locked_until=user_data.get("account_locked_until"),
                last_login=user_data.get("last_login", {}).get("$date"),
                created_at=user_data.get("created_at", {}).get("$date"),
                updated_at=user_data.get("updated_at", {}).get("$date"),
            )

            logger.debug(f"User object created: {new_user}")
            await new_user.save()
            logger.info(f"Created user: {old_user_id}")
            user_id_map[old_user_id] = str(new_user.id)

        except Exception as e:
            logger.error(f"Error migrating user {user_data.get('user_id')}: {e}")
            traceback.print_exc()

    return user_id_map


async def migrate_profiles(
    profiles_data: List[Dict[str, Any]], user_id_map: Dict[str, str]
) -> Dict[str, str]:
    """Migrate profiles from legacy data to new database."""
    profile_id_map = {}  # Map of old user_id to new profile_id

    for profile_data in profiles_data:
        try:
            old_user_id = profile_data.get("user_id")
            if not old_user_id or old_user_id not in user_id_map:
                logger.warning(f"Skipping profile without valid user_id: {old_user_id}")
                continue

            logger.debug(f"Processing profile for user: {old_user_id}")
            new_user_id = user_id_map[old_user_id]

            # Check if profile already exists
            existing_profile = await Profile.find_one({"user_id": new_user_id})
            if existing_profile:
                logger.info(f"Profile already exists for user: {old_user_id}")

                # Update existing profile with any new data
                personal_information = profile_data.get("personal_information", {})
                if personal_information:
                    existing_profile.personal_information = personal_information

                if profile_data.get("life_story"):
                    existing_profile.life_story = profile_data.get("life_story")

                # Get user preferences
                user_data = next(
                    (
                        u
                        for u in await load_json_file("user_information.users.json")
                        if u.get("user_id") == old_user_id
                    ),
                    None,
                )
                if user_data and "preferences" in user_data:
                    # Convert legacy preferences to new format
                    legacy_prefs = user_data["preferences"]
                    logger.debug(f"Found preferences for user: {old_user_id}")

                    # Create or update preferences
                    if not existing_profile.preferences:
                        existing_profile.preferences = Preferences()

                    # Update preferences
                    if "llm_preferences" in legacy_prefs:
                        existing_profile.preferences.llm_preferences = legacy_prefs.get(
                            "llm_preferences", {}
                        )

                    if "feature_preferences" in legacy_prefs:
                        existing_profile.preferences.feature_preferences = (
                            legacy_prefs.get("feature_preferences", {})
                        )

                    # Convert section preferences
                    if "section_preferences" in legacy_prefs:
                        section_prefs = legacy_prefs["section_preferences"]
                        # Convert from {"section": "action"} to {"sections_order": [], "visible_sections": []}
                        sections_order = list(section_prefs.keys())
                        visible_sections = [
                            s for s, action in section_prefs.items() if action != "Skip"
                        ]
                        existing_profile.preferences.section_preferences = {
                            "sections_order": sections_order,
                            "visible_sections": visible_sections,
                        }

                    # Add other preference categories
                    for category in [
                        "work_experience",
                        "education",
                        "skills",
                        "project_details",
                    ]:
                        if f"{category}_details" in legacy_prefs:
                            setattr(
                                existing_profile.preferences,
                                category,
                                legacy_prefs[f"{category}_details"],
                            )

                # Update timestamps if they exist in the data
                if profile_data.get("updated_at", {}).get("$date"):
                    existing_profile.updated_at = profile_data.get(
                        "updated_at", {}
                    ).get("$date")
                else:
                    existing_profile.updated_at = datetime.utcnow()

                await existing_profile.save()
                logger.info(f"Updated profile for user: {old_user_id}")
                profile_id_map[old_user_id] = str(existing_profile.id)
                continue

            # Get user preferences
            user_data = next(
                (
                    u
                    for u in await load_json_file("user_information.users.json")
                    if u.get("user_id") == old_user_id
                ),
                None,
            )
            preferences = None
            if user_data and "preferences" in user_data:
                # Convert legacy preferences to new format
                legacy_prefs = user_data["preferences"]
                logger.debug(f"Found preferences for user: {old_user_id}")

                # Create new preferences object
                preferences = Preferences(
                    llm_preferences=legacy_prefs.get("llm_preferences", {}),
                    feature_preferences=legacy_prefs.get("feature_preferences", {}),
                )

                # Convert section preferences
                if "section_preferences" in legacy_prefs:
                    section_prefs = legacy_prefs["section_preferences"]
                    # Convert from {"section": "action"} to {"sections_order": [], "visible_sections": []}
                    sections_order = list(section_prefs.keys())
                    visible_sections = [
                        s for s, action in section_prefs.items() if action != "Skip"
                    ]
                    preferences.section_preferences = {
                        "sections_order": sections_order,
                        "visible_sections": visible_sections,
                    }

                # Add other preference categories
                for category in [
                    "work_experience",
                    "education",
                    "skills",
                    "project_details",
                ]:
                    if f"{category}_details" in legacy_prefs:
                        setattr(
                            preferences, category, legacy_prefs[f"{category}_details"]
                        )

            # Create new profile
            personal_information = profile_data.get("personal_information", {})
            logger.debug(f"Creating profile with personal info: {personal_information}")

            new_profile = Profile(
                user_id=new_user_id,
                personal_information=personal_information,
                life_story=profile_data.get("life_story", ""),
                preferences=preferences,
                created_at=profile_data.get("created_at", {}).get(
                    "$date", datetime.utcnow()
                ),
                updated_at=profile_data.get("updated_at", {}).get(
                    "$date", datetime.utcnow()
                ),
            )

            logger.debug(f"Profile object created: {new_profile}")
            await new_profile.save()
            logger.info(f"Created profile for user: {old_user_id}")
            profile_id_map[old_user_id] = str(new_profile.id)

        except Exception as e:
            logger.error(
                f"Error migrating profile for user {profile_data.get('user_id')}: {e}"
            )
            traceback.print_exc()

    return profile_id_map


async def migrate_portfolios(
    portfolios_data: List[Dict[str, Any]], user_id_map: Dict[str, str]
) -> None:
    """Migrate portfolios from legacy data to new database."""
    for portfolio_data in portfolios_data:
        try:
            old_user_id = portfolio_data.get("user_id")
            if not old_user_id or old_user_id not in user_id_map:
                logger.warning(
                    f"Skipping portfolio without valid user_id: {old_user_id}"
                )
                continue

            logger.debug(f"Processing portfolio for user: {old_user_id}")
            new_user_id = user_id_map[old_user_id]

            # Check if portfolio already exists
            existing_portfolio = await Portfolio.find_one({"user_id": new_user_id})
            if existing_portfolio:
                logger.info(f"Portfolio already exists for user: {old_user_id}")

                # Update existing portfolio with any new data
                # Career summary
                career_summary_data = portfolio_data.get("career_summary", {})
                if career_summary_data:
                    logger.debug(f"Updating career summary data: {career_summary_data}")

                    if not existing_portfolio.career_summary:
                        existing_portfolio.career_summary = CareerSummary()

                    if "job_titles" in career_summary_data:
                        existing_portfolio.career_summary.job_titles = (
                            career_summary_data.get("job_titles", [])
                        )

                    if "years_of_experience" in career_summary_data:
                        existing_portfolio.career_summary.years_of_experience = (
                            career_summary_data.get("years_of_experience", "")
                        )

                    if "default_summary" in career_summary_data:
                        existing_portfolio.career_summary.default_summary = (
                            career_summary_data.get("default_summary", "")
                        )

                # Update other portfolio sections
                for field in [
                    "work_experience",
                    "education",
                    "skills",
                    "projects",
                    "awards",
                    "publications",
                    "certifications",
                    "languages",
                ]:
                    if field in portfolio_data and portfolio_data[field]:
                        setattr(existing_portfolio, field, portfolio_data[field])

                if "professional_title" in portfolio_data:
                    existing_portfolio.professional_title = portfolio_data.get(
                        "professional_title", ""
                    )

                # Update timestamp
                existing_portfolio.updated_at = datetime.utcnow()

                await existing_portfolio.save()
                logger.info(f"Updated portfolio for user: {old_user_id}")
                continue

            # Create career summary
            career_summary_data = portfolio_data.get("career_summary", {})
            logger.debug(f"Career summary data: {career_summary_data}")

            career_summary = CareerSummary(
                job_titles=career_summary_data.get("job_titles", []),
                years_of_experience=career_summary_data.get("years_of_experience", ""),
                default_summary=career_summary_data.get("default_summary", ""),
            )

            # Create new portfolio
            logger.debug(f"Creating portfolio for user: {old_user_id}")
            new_portfolio = Portfolio(
                user_id=new_user_id,
                career_summary=career_summary,
                work_experience=portfolio_data.get("work_experience", []),
                education=portfolio_data.get("education", []),
                skills=portfolio_data.get("skills", []),
                projects=portfolio_data.get("projects", []),
                awards=portfolio_data.get("awards", []),
                publications=portfolio_data.get("publications", []),
                certifications=portfolio_data.get("certifications", []),
                languages=portfolio_data.get("languages", []),
                professional_title=portfolio_data.get("professional_title", ""),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            logger.debug(f"Portfolio object created: {new_portfolio}")
            await new_portfolio.save()
            logger.info(f"Created portfolio for user: {old_user_id}")

        except Exception as e:
            logger.error(
                f"Error migrating portfolio for user {portfolio_data.get('user_id')}: {e}"
            )
            traceback.print_exc()


async def main():
    """Main migration function."""
    logger.info("Starting data migration")

    # Initialize database with the correct database name
    await initialize_database()
    logger.info("Database initialized")

    # Load data from JSON files
    users_data = await load_json_file("user_information.users.json")
    profiles_data = await load_json_file("user_information.profiles.json")
    portfolios_data = await load_json_file("user_information.portfolio.json")

    # Migrate users first to get user ID mapping
    user_id_map = await migrate_users(users_data)
    logger.info(f"Migrated {len(user_id_map)} users")

    # Migrate profiles
    profile_id_map = await migrate_profiles(profiles_data, user_id_map)
    logger.info(f"Migrated {len(profile_id_map)} profiles")

    # Migrate portfolios
    await migrate_portfolios(portfolios_data, user_id_map)
    logger.info("Migration completed")


if __name__ == "__main__":
    asyncio.run(main())
