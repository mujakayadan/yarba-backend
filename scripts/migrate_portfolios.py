#!/usr/bin/env python
"""
Script to migrate portfolios from legacy JSON files to the new MongoDB database.
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

# Add parent directory to path to import core modules
sys.path.append(str(Path(__file__).parent.parent))
from core.database.connections.mongo import mongo_manager
from core.models.portfolio import (
    Award,
    CareerSummary,
    CustomSections,
    Education,
    Portfolio,
    PortfolioItem,
    Project,
    Publication,
    SkillCategory,
    WorkExperience,
)
from core.models.profile import Profile
from core.models.user import User

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def load_environment() -> Dict[str, str]:
    """Load environment variables from the correct .env file."""
    current_dir = Path(__file__).parent.parent
    new_env_path = current_dir / ".env"
    root_env_path = current_dir.parent / ".env"

    if new_env_path.exists():
        logger.info(f"Loading environment from: {new_env_path}")
        load_dotenv(dotenv_path=new_env_path, override=True)
    elif root_env_path.exists():
        logger.info(f"Loading environment from: {root_env_path}")
        load_dotenv(dotenv_path=root_env_path, override=True)
    else:
        logger.warning("No .env file found!")

    return {
        "MONGODB_URI": os.getenv("MONGODB_URI", "mongodb://localhost:27017/"),
        "MONGODB_DATABASE": os.getenv("MONGODB_DATABASE", "rbt"),
    }


def load_json_file(filename: str) -> list:
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


def convert_mongo_date(date_obj) -> datetime:
    """Convert MongoDB date object to Python datetime."""
    if date_obj is None:
        return datetime.utcnow()
    if isinstance(date_obj, dict) and "$date" in date_obj:
        return datetime.fromisoformat(date_obj["$date"].replace("Z", "+00:00"))
    return date_obj if isinstance(date_obj, datetime) else datetime.utcnow()


def load_user_id_map() -> Dict[str, str]:
    """Load the user ID map from file."""
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


def load_profile_id_map() -> Dict[str, str]:
    """Load the profile ID map from file."""
    try:
        with open("profile_id_map.json", "r") as f:
            profile_id_map = json.load(f)
            logger.info(f"Loaded profile ID map with {len(profile_id_map)} mappings")
            return profile_id_map
    except FileNotFoundError:
        logger.error("Profile ID map file not found")
        return {}
    except json.JSONDecodeError:
        logger.error("Invalid JSON in profile ID map file")
        return {}


async def migrate_portfolios() -> Dict[str, str]:
    """Migrate portfolios from legacy data to new database."""
    # Load environment variables
    env = load_environment()

    # Initialize MongoDB connection using the manager
    mongo_manager.initialize(env["MONGODB_URI"], env["MONGODB_DATABASE"])

    # Initialize Beanie with the managed connection
    await init_beanie(
        database=mongo_manager.async_db,
        document_models=[User, Profile, Portfolio, PortfolioItem],
    )
    logger.info(f"Connected to database: {env['MONGODB_DATABASE']}")

    # Load ID maps
    user_id_map = load_user_id_map()
    profile_id_map = load_profile_id_map()
    if not user_id_map:
        logger.error("No user ID map found, cannot migrate portfolios")
        return {}

    # Load portfolio data
    portfolios_data = load_json_file("user_information.portfolio.json")
    if not portfolios_data:
        logger.error("No portfolios data found")
        return {}

    # Map of old portfolio_id to new portfolio_id
    portfolio_id_map = {}

    # Process each portfolio
    for portfolio_data in portfolios_data:
        try:
            user_id = portfolio_data.get("user_id")
            if not user_id:
                logger.warning(f"Skipping portfolio without user_id: {portfolio_data}")
                continue

            # Check if user exists in the map
            if user_id not in user_id_map:
                logger.warning(f"User ID not found in map: {user_id}")
                continue

            new_user_id = ObjectId(user_id_map[user_id])

            # Get profile ID if available
            profile_id = portfolio_data.get("profile_id")
            new_profile_id = (
                ObjectId(profile_id_map[profile_id])
                if profile_id and profile_id in profile_id_map
                else None
            )

            # Check if portfolio already exists
            existing_portfolio = await Portfolio.find_one(
                Portfolio.user_id == new_user_id
            )
            if existing_portfolio:
                logger.info(f"Portfolio already exists for user: {user_id}")
                portfolio_id_map[
                    str(portfolio_data.get("_id", {}).get("$oid", user_id))
                ] = str(existing_portfolio.id)
                continue

            # Create career summary
            career_summary = CareerSummary(
                job_titles=portfolio_data.get("career_summary", {}).get(
                    "job_titles", []
                ),
                years_of_experience=str(
                    portfolio_data.get("career_summary", {}).get(
                        "years_of_experience", ""
                    )
                ),
                default_summary=portfolio_data.get("career_summary", {}).get(
                    "default_summary", ""
                ),
            )

            # Convert skills to SkillCategory objects
            skills = []
            for skill_data in portfolio_data.get("skills", []):
                for category, skill_list in skill_data.items():
                    skills.append(SkillCategory(category=category, skills=skill_list))

            # Convert work experience entries
            work_experience = [
                WorkExperience(
                    job_title=exp.get("job_title", ""),
                    company=exp.get("company", ""),
                    location=exp.get("location", ""),
                    time=exp.get("time", ""),
                    responsibilities=exp.get("responsibilities", []),
                )
                for exp in portfolio_data.get("work_experience", [])
            ]

            # Convert education entries
            education = [
                Education(
                    degree_type=edu.get("degree_type", ""),
                    degree=edu.get("degree", ""),
                    university_name=edu.get("university_name", ""),
                    time=edu.get("time", ""),
                    location=edu.get("location", ""),
                    GPA=str(edu.get("GPA", "")),
                    transcript=edu.get("transcript", []),
                )
                for edu in portfolio_data.get("education", [])
            ]

            # Convert project entries
            projects = [
                Project(
                    name=proj.get("name", ""),
                    bullet_points=proj.get("bullet_points", []),
                    date=proj.get("date", ""),
                )
                for proj in portfolio_data.get("projects", [])
            ]

            # Convert award entries
            awards = [
                Award(
                    name=award.get("name", ""), explanation=award.get("explanation", "")
                )
                for award in portfolio_data.get("awards", [])
            ]

            # Convert publication entries
            publications = [
                Publication(
                    name=pub.get("name", ""),
                    publisher=pub.get("publisher", ""),
                    link=pub.get("link", ""),
                    time=pub.get("time", ""),
                )
                for pub in portfolio_data.get("publications", [])
            ]

            # Create custom sections
            custom_sections = CustomSections(
                enabled=portfolio_data.get("custom_sections", {}).get("enabled", []),
                order=portfolio_data.get("custom_sections", {}).get("order", []),
            )

            # Create a new portfolio using the Beanie model
            new_portfolio = Portfolio(
                user_id=new_user_id,
                profile_id=new_profile_id,
                title=portfolio_data.get("title", ""),
                description=portfolio_data.get("description", ""),
                professional_title=portfolio_data.get("professional_title"),
                career_summary=career_summary,
                skills=skills,
                work_experience=work_experience,
                education=education,
                projects=projects,
                awards=awards,
                publications=publications,
                certifications=portfolio_data.get("certifications", []),
                custom_sections=custom_sections,
                is_active=portfolio_data.get("is_active", True),
                version=portfolio_data.get("version", "1.0"),
                created_at=convert_mongo_date(portfolio_data.get("created_at")),
                updated_at=convert_mongo_date(portfolio_data.get("updated_at")),
            )

            # Save the portfolio using Beanie
            await new_portfolio.save()
            logger.info(
                f"Created portfolio for user: {user_id}, ID: {new_portfolio.id}"
            )
            portfolio_id_map[
                str(portfolio_data.get("_id", {}).get("$oid", user_id))
            ] = str(new_portfolio.id)

        except Exception as e:
            logger.error(f"Error migrating portfolio for user {user_id}: {e}")

    # Save the portfolio ID map to a file
    try:
        with open("portfolio_id_map.json", "w") as f:
            json.dump(portfolio_id_map, f, indent=2)
        logger.info(f"Saved portfolio ID map with {len(portfolio_id_map)} mappings")
    except Exception as e:
        logger.error(f"Error saving portfolio ID map: {e}")

    # Close the connection when done
    mongo_manager.close_async_connection()
    logger.info(f"Migrated {len(portfolio_id_map)} portfolios")
    return portfolio_id_map


async def main():
    """Main function to run the migration."""
    try:
        logger.info("Starting portfolio migration")
        await migrate_portfolios()
        logger.info("Portfolio migration completed")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
