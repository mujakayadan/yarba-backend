#!/usr/bin/env python
"""
Script to migrate portfolio items from legacy JSON files to the new MongoDB database.
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
from core.models.portfolio import Portfolio, PortfolioItem
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


def load_portfolio_id_map() -> Dict[str, str]:
    """Load the portfolio ID map from file."""
    try:
        with open("portfolio_id_map.json", "r") as f:
            portfolio_id_map = json.load(f)
            logger.info(
                f"Loaded portfolio ID map with {len(portfolio_id_map)} mappings"
            )
            return portfolio_id_map
    except FileNotFoundError:
        logger.error("Portfolio ID map file not found")
        return {}
    except json.JSONDecodeError:
        logger.error("Invalid JSON in portfolio ID map file")
        return {}


async def migrate_portfolio_items() -> Dict[str, str]:
    """Migrate portfolio items from legacy data to new database."""
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

    # Load portfolio ID map
    portfolio_id_map = load_portfolio_id_map()
    if not portfolio_id_map:
        logger.error("No portfolio ID map found, cannot migrate portfolio items")
        return {}

    # Load portfolio items data
    items_data = load_json_file("user_information.portfolio_items.json")
    if not items_data:
        logger.error("No portfolio items data found")
        return {}

    # Map of old item_id to new item_id
    item_id_map = {}

    # Process each portfolio item
    for item_data in items_data:
        try:
            portfolio_id = item_data.get("portfolio_id")
            if not portfolio_id:
                logger.warning(f"Skipping item without portfolio_id: {item_data}")
                continue

            # Check if portfolio exists in the map
            if portfolio_id not in portfolio_id_map:
                logger.warning(f"Portfolio ID not found in map: {portfolio_id}")
                continue

            new_portfolio_id = ObjectId(portfolio_id_map[portfolio_id])

            # Check if portfolio exists
            portfolio = await Portfolio.get(new_portfolio_id)
            if not portfolio:
                logger.warning(f"Portfolio not found: {new_portfolio_id}")
                continue

            # Create a new portfolio item
            new_item = PortfolioItem(
                portfolio_id=new_portfolio_id,
                title=item_data.get("title", ""),
                description=item_data.get("description", ""),
                type=item_data.get("type", ""),
                url=item_data.get("url", ""),
                bullet_points=item_data.get("bullet_points", []),
                tags=item_data.get("tags", []),
                date=item_data.get("date", ""),
                order=item_data.get("order", 0),
                is_featured=item_data.get("is_featured", False),
                company=item_data.get("company", ""),
                location=item_data.get("location", ""),
                created_at=convert_mongo_date(item_data.get("created_at")),
                updated_at=convert_mongo_date(item_data.get("updated_at")),
            )

            # Save the portfolio item
            await new_item.save()
            logger.info(
                f"Created portfolio item: {new_item.id} for portfolio: {portfolio_id}"
            )
            item_id_map[str(item_data.get("_id", {}).get("$oid", ""))] = str(
                new_item.id
            )

        except Exception as e:
            logger.error(f"Error migrating portfolio item: {e}")

    # Save the item ID map to a file
    try:
        with open("portfolio_item_id_map.json", "w") as f:
            json.dump(item_id_map, f, indent=2)
        logger.info(f"Saved portfolio item ID map with {len(item_id_map)} mappings")
    except Exception as e:
        logger.error(f"Error saving portfolio item ID map: {e}")

    # Close the connection when done
    mongo_manager.close_async_connection()
    logger.info(f"Migrated {len(item_id_map)} portfolio items")
    return item_id_map


async def main():
    """Main function to run the migration."""
    try:
        logger.info("Starting portfolio items migration")
        await migrate_portfolio_items()
        logger.info("Portfolio items migration completed")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
