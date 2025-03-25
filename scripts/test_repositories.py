#!/usr/bin/env python
"""
Script to test enhanced repository methods.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path to import core modules
sys.path.append(str(Path(__file__).parent.parent))

from core.database.init import init_db
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.profile_repository import ProfileRepository

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def test_repositories():
    """Test the enhanced repository methods."""
    # Initialize DB
    await init_db()
    logger.info("Database initialized")

    # Test user ID (replace with a valid user ID from your database)
    test_user_id = "67d713143f8ee422d6db534a"
    logger.info(f"Using test user ID: {test_user_id}")

    # Test profile repository
    logger.info("Testing ProfileRepository...")
    profile_repo = ProfileRepository()

    # Get profile
    profile = await profile_repo.get_by_user_id(test_user_id)
    if profile:
        logger.info(f"Found profile for user {test_user_id}")
        print(f"\n{'='*40}")
        print("PROFILE")
        print(f"{'='*40}")
        print(f"Name: {profile.full_name}")
        print(f"Email: {profile.email}")

        # Get preferences
        preferences = await profile_repo.get_preferences(test_user_id)
        if preferences:
            print(f"\n{'='*40}")
            print("PREFERENCES")
            print(f"{'='*40}")
            print(json.dumps(preferences.model_dump(), indent=2))
    else:
        logger.warning(f"No profile found for user {test_user_id}")

    # Test portfolio repository
    logger.info("Testing PortfolioRepository...")
    portfolio_repo = PortfolioRepository()

    # Get portfolio
    portfolio = await portfolio_repo.get_portfolio_by_user_id(test_user_id)
    if portfolio:
        logger.info(f"Found portfolio for user {test_user_id}")

        # Test individual sections
        print(f"\n{'='*40}")
        print("CAREER SUMMARY")
        print(f"{'='*40}")
        career_summary = await portfolio_repo.get_career_summary(test_user_id)
        if career_summary:
            print(json.dumps(career_summary.model_dump(), indent=2))

        print(f"\n{'='*40}")
        print("SKILLS")
        print(f"{'='*40}")
        skills = await portfolio_repo.get_skills(test_user_id)
        print(f"Found {len(skills)} skills")
        for skill in skills[:3]:  # Show first 3 skills
            print(f"- {skill.name} ({skill.level})")

        print(f"\n{'='*40}")
        print("PUBLICATIONS")
        print(f"{'='*40}")
        publications = await portfolio_repo.get_publications(test_user_id)
        print(f"Found {len(publications)} publications")
        for pub in publications[:3]:  # Show first 3 publications
            print(f"- {pub.title} ({pub.year})")

        print(f"\n{'='*40}")
        print("WORK EXPERIENCE")
        print(f"{'='*40}")
        work_experience = await portfolio_repo.get_work_experience(test_user_id)
        print(f"Found {len(work_experience)} work experiences")
        if work_experience:
            job = work_experience[0]
            print(f"- {job.title} at {job.company}")
    else:
        logger.warning(f"No portfolio found for user {test_user_id}")

    logger.info("Repository testing completed")


if __name__ == "__main__":
    asyncio.run(test_repositories())
