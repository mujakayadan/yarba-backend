"""Portfolio loader for loading and processing portfolio data."""

import asyncio
import logging
from typing import Any, Dict, Optional

from config.logging_config import get_logger
from config.settings import Settings
from core.database.init import init_db
from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.models.user import User

logger = get_logger(__name__)
settings = Settings()

if __name__ == "__main__":
    import sys
    from pathlib import Path

    project_root = str(Path(__file__).parent.parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


class PortfolioLoader:
    """A class to load user portfolio information.

    This class handles the loading and processing of portfolio data,
    combining information from both portfolio and profile collections.
    """

    def __init__(self, user_id: str):
        """Initialize the loader for a specific user.

        Args:
            user_id: The user ID (can be ObjectId string or username) to load portfolio data for
        """
        self.user_id = user_id
        self._portfolio = None
        self._profile = None
        self._db_initialized = False
        logger.debug(f"Initialized PortfolioLoader for user: {self.user_id}")

    async def _initialize_db(self) -> bool:
        """Initialize the database connection."""
        if not self._db_initialized:
            try:
                # Initialize the database with Beanie
                client = await init_db()
                if client:
                    self._db_initialized = True
                    logger.info("Database initialized successfully")
                    return True
                else:
                    logger.error("Failed to initialize database")
                    return False
            except Exception as e:
                logger.error(f"Error initializing database: {e}")
                return False
        return True

    async def _load_data(self) -> None:
        """Load portfolio and profile data using Beanie ODM."""
        if self._portfolio is None:
            try:
                # Initialize the database first
                if not await self._initialize_db():
                    logger.error("Cannot load data without database initialization")
                    return

                logger.info(f"Looking for user with ID: {self.user_id}")

                # Try to find the user by ID or username
                user = await User.find_one({"email": self.user_id})
                if not user:
                    logger.debug(
                        f"User not found by email, trying with user_id: {self.user_id}"
                    )

                # Get profile data
                logger.info(f"Looking for profile with user_id: {self.user_id}")
                self._profile = await Profile.find_one({"user.id": self.user_id})

                if not self._profile:
                    # Try finding by user_id field
                    self._profile = await Profile.find_one({"user_id": self.user_id})

                logger.debug(f"Profile query result: {self._profile}")
                if not self._profile:
                    logger.warning(f"Profile not found for user_id {self.user_id}")

                # Get portfolio data
                logger.info(f"Looking for portfolio with user_id: {self.user_id}")
                self._portfolio = await Portfolio.find_one({"user.id": self.user_id})

                if not self._portfolio:
                    # Try finding by user_id field
                    self._portfolio = await Portfolio.find_one(
                        {"user_id": self.user_id}
                    )

                logger.debug(f"Portfolio query result: {self._portfolio}")
                if not self._portfolio:
                    logger.warning(f"Portfolio not found for user_id {self.user_id}")

            except Exception as e:
                logger.error(
                    f"Error loading data for user {self.user_id}: {e}", exc_info=True
                )
                raise

    async def get_section_data(self, section: str) -> Optional[Any]:
        """Get data for a specific section.

        Args:
            section: The name of the section to retrieve

        Returns:
            Optional[Any]: The data for the requested section, or None if not found
        """
        await self._load_data()
        logger.debug(f"Getting data for section: {section}")

        if not self._portfolio:
            logger.warning(f"No portfolio found for user {self.user_id}")
            return None

        if section == "personal_information":
            # Construct personal information from profile fields
            personal_info = {
                "name": self._profile.full_name if self._profile else None,
                "email": self._profile.email if self._profile else None,
                "phone": self._profile.phone if self._profile else None,
                "address": self._profile.address if self._profile else None,
                "city": self._profile.city if self._profile else None,
                "state": self._profile.state if self._profile else None,
                "zip_code": self._profile.zip_code if self._profile else None,
                "country": self._profile.country if self._profile else None,
                "linkedin": self._profile.linkedin if self._profile else None,
                "github": self._profile.github if self._profile else None,
                "website": self._profile.website if self._profile else None,
            }
            logger.debug(f"Found personal information: {personal_info}")
            return personal_info

        # Try to get data from portfolio first
        if hasattr(self._portfolio, section):
            data = getattr(self._portfolio, section)
            logger.debug(f"Found data for section {section} in portfolio: {data}")
            return data

        # Fallback to profile if data not found in portfolio
        if self._profile and hasattr(self._profile, section):
            data = getattr(self._profile, section)
            logger.debug(f"Found data for section {section} in profile: {data}")
            return data

        logger.warning(f"Section {section} not found in portfolio or profile")
        return None

    async def get_all_sections(self) -> Dict[str, Any]:
        """Get all sections from the portfolio.

        Returns:
            Dict[str, Any]: A dictionary containing all portfolio sections
        """
        await self._load_data()

        sections = {
            "personal_information": await self.get_section_data("personal_information"),
            "career_summary": await self.get_section_data("career_summary"),
            "work_experience": await self.get_section_data("work_experience"),
            "skills": await self.get_section_data("skills"),
            "education": await self.get_section_data("education"),
            "projects": await self.get_section_data("projects"),
            "awards": await self.get_section_data("awards"),
            "publications": await self.get_section_data("publications"),
            "languages": await self.get_section_data("languages"),
            "certifications": await self.get_section_data("certifications"),
        }
        return sections

    def refresh(self) -> None:
        """Force reload of portfolio data."""
        self._portfolio = None
        self._profile = None


async def main():
    """Main function to test the PortfolioLoader."""
    # Set up logging
    logging.basicConfig(level=logging.DEBUG)
    logger.info("Initializing portfolio loader test")

    # Use the test user ID from settings
    test_user_id = settings.test_user_id
    logger.info(f"Using test user ID: {test_user_id}")

    # Example usage
    portfolio_loader = PortfolioLoader(test_user_id)

    print("\nLoading all sections...")
    all_sections = await portfolio_loader.get_all_sections()

    # Print each section with a header
    for section_name, section_data in all_sections.items():
        print(f"\n{'='*40}")
        print(f"{section_name.upper()}")
        print(f"{'='*40}\n")
        if isinstance(section_data, dict):
            for key, value in section_data.items():
                if value is not None:  # Only print non-None values
                    print(f"{key}: {value}")
        elif isinstance(section_data, list):
            for item in section_data:
                if isinstance(item, dict):
                    print("\nItem:")
                    for key, value in item.items():
                        print(f"  {key}: {value}")
                else:
                    print(f"- {item}")
        elif section_data is not None:
            print(section_data)

    print("\nLoading portfolio items...")
    portfolio_items = await portfolio_loader.get_portfolio_items()
    print(f"\n{'='*40}")
    print("PORTFOLIO ITEMS")
    print(f"{'='*40}\n")
    for item in portfolio_items:
        if hasattr(item, "title"):
            print(f"Title: {item.title}")
            print(f"Description: {item.description}")
            print(f"Type: {item.type}")
            if hasattr(item, "technologies") and item.technologies:
                print(f"Technologies: {', '.join(item.technologies)}")
            if hasattr(item, "url") and item.url:
                print(f"URL: {item.url}")
            print()


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
