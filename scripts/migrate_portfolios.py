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
from typing import Dict, List, Optional, Tuple

from beanie import init_beanie
from bson import ObjectId
from dotenv import load_dotenv
from tqdm import tqdm

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
    Skill,
    WorkExperience,
)
from core.models.profile import Profile
from core.models.user import User
from core.repositories.portfolio import PortfolioItemRepository, PortfolioRepository

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("portfolio_migration.log"),
    ],
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


def load_id_maps() -> Tuple[Dict[str, str], Dict[str, str]]:
    """Load user and profile ID maps from files."""
    user_id_map = {}
    profile_id_map = {}

    try:
        with open("user_id_map.json", "r") as f:
            user_id_map = json.load(f)
            logger.info(f"Loaded user ID map with {len(user_id_map)} mappings")
    except FileNotFoundError:
        logger.error("User ID map file not found")
    except json.JSONDecodeError:
        logger.error("Invalid JSON in user ID map file")

    try:
        with open("profile_id_map.json", "r") as f:
            profile_id_map = json.load(f)
            logger.info(f"Loaded profile ID map with {len(profile_id_map)} mappings")
    except FileNotFoundError:
        logger.error("Profile ID map file not found")
    except json.JSONDecodeError:
        logger.error("Invalid JSON in profile ID map file")

    return user_id_map, profile_id_map


def validate_portfolio_data(portfolio_data: Dict) -> Tuple[bool, str]:
    """
    Validate portfolio data before migration.

    Args:
        portfolio_data: Portfolio data to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not portfolio_data.get("user_id"):
        return False, "Missing user_id"
    return True, ""


async def process_skills(skills_data: List[Dict]) -> List[Skill]:
    """
    Process and validate skills data.

    Args:
        skills_data: List of skill data dictionaries

    Returns:
        List of validated Skill objects
    """
    skills = []
    for skill_category in skills_data:
        try:
            if isinstance(skill_category, dict):
                for category, skill_list in skill_category.items():
                    if isinstance(skill_list, list):
                        # Filter out any non-string or empty skills
                        valid_skills = [
                            str(s) for s in skill_list if s and str(s).strip()
                        ]
                        if valid_skills:
                            skill = Skill(category=category, skills=valid_skills)
                            skills.append(skill)
                            logger.debug(
                                f"Added skill category: {category} with {len(valid_skills)} skills"
                            )
        except Exception as e:
            logger.error(f"Error processing skill category {skill_category}: {e}")
            continue
    return skills


def get_object_id(data: Dict) -> str:
    """Extract ObjectId from MongoDB data safely."""
    logger.debug(f"Extracting ObjectId from data: {data}")
    if isinstance(data, dict):
        if "$oid" in data:
            result = str(data["$oid"])
            logger.debug(f"Found $oid in dict, returning: {result}")
            return result
        id_value = data.get("_id")
        logger.debug(f"Found _id in dict: {id_value}")
        if isinstance(id_value, dict):
            oid = id_value.get("$oid", "")
            logger.debug(f"_id is dict, extracted $oid: {oid}")
            return str(oid)
        return str(id_value) if id_value else ""
    return str(data)


async def migrate_portfolios() -> Dict[str, str]:
    """Migrate portfolios from legacy data to new database."""
    # Load environment variables and initialize connections
    env = load_environment()
    mongo_manager.initialize(env["MONGODB_URI"], env["MONGODB_DATABASE"])
    await init_beanie(
        database=mongo_manager.async_db,
        document_models=[User, Profile, Portfolio, PortfolioItem],
    )
    logger.info(f"Connected to database: {env['MONGODB_DATABASE']}")

    # Initialize repositories
    portfolio_repo = PortfolioRepository()

    # Load ID maps and portfolio data
    user_id_map, profile_id_map = load_id_maps()
    if not user_id_map:
        logger.error("No user ID map found, cannot migrate portfolios")
        return {}

    portfolios_data = load_json_file("user_information.portfolio.json")
    if not portfolios_data:
        logger.error("No portfolios data found")
        return {}

    # Map of old portfolio_id to new portfolio_id
    portfolio_id_map = {}
    migration_errors = []

    # Process each portfolio with progress bar
    for portfolio_data in tqdm(portfolios_data, desc="Migrating portfolios"):
        try:
            logger.debug(
                f"Processing portfolio data: {json.dumps(portfolio_data, default=str)}"
            )

            # Validate portfolio data
            is_valid, error_msg = validate_portfolio_data(portfolio_data)
            if not is_valid:
                logger.warning(f"Invalid portfolio data: {error_msg}")
                portfolio_id = get_object_id(portfolio_data.get("_id"))
                logger.debug(f"Invalid portfolio ID: {portfolio_id}")
                migration_errors.append({"portfolio": portfolio_id, "error": error_msg})
                continue

            user_id = portfolio_data.get("user_id")
            logger.debug(f"Processing user_id: {user_id}")
            if not user_id:
                logger.warning("User ID is None or empty")
                continue

            if isinstance(user_id, dict):
                user_id = get_object_id(user_id)
                logger.debug(f"Converted dict user_id to string: {user_id}")

            if user_id not in user_id_map:
                logger.warning(f"User ID not found in map: {user_id}")
                continue

            new_user_id = ObjectId(user_id_map[user_id])
            logger.debug(f"Processing portfolio for user: {user_id} -> {new_user_id}")

            # Get profile ID if available
            profile_id = portfolio_data.get("profile_id")
            logger.debug(f"Found profile_id: {profile_id}")
            if isinstance(profile_id, dict):
                profile_id = get_object_id(profile_id)
                logger.debug(f"Converted dict profile_id to string: {profile_id}")

            new_profile_id = None
            if profile_id and profile_id in profile_id_map:
                new_profile_id = ObjectId(profile_id_map[profile_id])
                logger.debug(f"Mapped profile_id: {profile_id} -> {new_profile_id}")

            # Check for existing portfolio
            existing_portfolio = await portfolio_repo.get_active_by_user_id(
                str(new_user_id)
            )
            if existing_portfolio:
                logger.info(f"Portfolio already exists for user: {user_id}")
                old_id = get_object_id(portfolio_data.get("_id"))
                logger.debug(f"Found existing portfolio, mapping old_id: {old_id}")
                if old_id:
                    portfolio_id_map[old_id] = str(existing_portfolio.id)
                    logger.debug(
                        f"Mapped existing portfolio: {old_id} -> {existing_portfolio.id}"
                    )
                continue

            # Process and validate skills
            skills = await process_skills(portfolio_data.get("skills", []))

            # Convert work experience entries with validation
            work_experience = [
                WorkExperience(
                    job_title=str(exp.get("job_title", "")),
                    company=str(exp.get("company", "")),
                    location=str(exp.get("location", "")),
                    time=str(exp.get("time", "")),
                    responsibilities=[
                        str(r) for r in exp.get("responsibilities", []) if r
                    ],
                )
                for exp in portfolio_data.get("work_experience", [])
                if exp.get("job_title") or exp.get("company")
            ]

            # Convert education entries with validation
            education = [
                Education(
                    degree_type=str(edu.get("degree_type", "")),
                    degree=str(edu.get("degree", "")),
                    university_name=str(edu.get("university_name", "")),
                    time=str(edu.get("time", "")),
                    location=str(edu.get("location", "")),
                    GPA=str(edu.get("GPA", "")),
                    transcript=[str(t) for t in edu.get("transcript", []) if t],
                )
                for edu in portfolio_data.get("education", [])
                if edu.get("degree") or edu.get("university_name")
            ]

            # Convert project entries with validation
            projects = [
                Project(
                    name=str(proj.get("name", "")),
                    bullet_points=[str(b) for b in proj.get("bullet_points", []) if b],
                    date=str(proj.get("date", "")),
                )
                for proj in portfolio_data.get("projects", [])
                if proj.get("name")
            ]

            # Convert award entries with validation
            awards = [
                Award(
                    name=str(award.get("name", "")),
                    explanation=str(award.get("explanation", "")),
                )
                for award in portfolio_data.get("awards", [])
                if award.get("name")
            ]

            # Convert publication entries with validation
            publications = [
                Publication(
                    name=str(pub.get("name", "")),
                    publisher=str(pub.get("publisher", "")),
                    link=str(pub.get("link", "")),
                    time=str(pub.get("time", "")),
                )
                for pub in portfolio_data.get("publications", [])
                if pub.get("name")
            ]

            # Create custom sections with validation
            custom_sections = CustomSections(
                enabled=[
                    str(s)
                    for s in portfolio_data.get("custom_sections", {}).get(
                        "enabled", []
                    )
                    if s
                ],
                order=[
                    str(s)
                    for s in portfolio_data.get("custom_sections", {}).get("order", [])
                    if s
                ],
            )

            # Create career summary with validation
            career_summary = CareerSummary(
                job_titles=[
                    str(t)
                    for t in portfolio_data.get("career_summary", {}).get(
                        "job_titles", []
                    )
                    if t
                ],
                years_of_experience=str(
                    portfolio_data.get("career_summary", {}).get(
                        "years_of_experience", ""
                    )
                ),
                default_summary=str(
                    portfolio_data.get("career_summary", {}).get("default_summary", "")
                ),
            )

            # Create a new portfolio using the repository
            logger.debug("Creating new portfolio")
            new_portfolio = await portfolio_repo.create_for_user(
                str(new_user_id),
                str(new_profile_id) if new_profile_id else None,
            )
            logger.debug(f"Created new portfolio with ID: {new_portfolio.id}")

            # Update portfolio fields
            new_portfolio.professional_title = str(
                portfolio_data.get("professional_title", "")
            )
            new_portfolio.career_summary = career_summary
            new_portfolio.skills = skills
            new_portfolio.work_experience = work_experience
            new_portfolio.education = education
            new_portfolio.projects = projects
            new_portfolio.awards = awards
            new_portfolio.publications = publications
            new_portfolio.certifications = [
                str(cert) for cert in portfolio_data.get("certifications", []) if cert
            ]
            new_portfolio.custom_sections = custom_sections
            new_portfolio.is_active = bool(portfolio_data.get("is_active", True))
            new_portfolio.version = str(portfolio_data.get("version", "1.0"))
            new_portfolio.created_at = convert_mongo_date(
                portfolio_data.get("created_at")
            )
            new_portfolio.updated_at = convert_mongo_date(
                portfolio_data.get("updated_at")
            )

            # Save the updated portfolio
            await new_portfolio.replace()
            logger.info(
                f"Updated portfolio for user: {user_id}, ID: {new_portfolio.id}"
            )

            # Map the old ID to new ID
            old_id = get_object_id(portfolio_data.get("_id"))
            logger.debug(f"Mapping portfolio IDs: {old_id} -> {new_portfolio.id}")
            if old_id:
                portfolio_id_map[old_id] = str(new_portfolio.id)
                logger.debug(
                    f"Added to portfolio_id_map: {old_id} -> {new_portfolio.id}"
                )

        except Exception as e:
            error_msg = f"Error migrating portfolio for user {portfolio_data.get('user_id')}: {e}"
            logger.error(error_msg)
            logger.error(
                f"Portfolio data causing error: {json.dumps(portfolio_data, default=str)}"
            )
            logger.exception("Full traceback:")  # This will log the full stack trace
            migration_errors.append(
                {
                    "portfolio": get_object_id(portfolio_data.get("_id")),
                    "error": str(e),
                    "user_id": str(portfolio_data.get("user_id")),
                }
            )

    # Save the portfolio ID map
    try:
        with open("portfolio_id_map.json", "w") as f:
            json.dump(portfolio_id_map, f, indent=2)
        logger.info(f"Saved portfolio ID map with {len(portfolio_id_map)} mappings")
    except Exception as e:
        logger.error(f"Error saving portfolio ID map: {e}")

    # Save migration errors if any
    if migration_errors:
        try:
            with open("portfolio_migration_errors.json", "w") as f:
                json.dump(migration_errors, f, indent=2)
            logger.warning(
                f"Migration completed with {len(migration_errors)} errors. See portfolio_migration_errors.json for details."
            )
        except Exception as e:
            logger.error(f"Error saving migration errors: {e}")

    # Close the connection
    mongo_manager.close_async_connection()
    logger.info(
        f"Migration completed. Successfully migrated {len(portfolio_id_map)} portfolios."
    )
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
