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
from typing import Dict, List, Optional, Tuple

from beanie import init_beanie
from bson import ObjectId
from dotenv import load_dotenv
from tqdm import tqdm

# Add parent directory to path to import core modules
sys.path.append(str(Path(__file__).parent.parent))
from core.database.connections.mongo import mongo_manager
from core.models.portfolio import Portfolio, PortfolioItem
from core.models.profile import Profile
from core.models.user import User
from core.repositories.portfolio_repository import (
    PortfolioItemRepository,
    PortfolioRepository,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("portfolio_items_migration.log"),
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


def load_portfolio_id_map() -> Dict[str, str]:
    """Load portfolio ID map from file."""
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


def validate_portfolio_item_data(item_data: Dict) -> Tuple[bool, str]:
    """
    Validate portfolio item data before migration.

    Args:
        item_data: Portfolio item data to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not item_data.get("portfolio_id"):
        return False, "Missing portfolio_id"

    required_fields = ["title", "type"]
    missing_fields = [field for field in required_fields if not item_data.get(field)]
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"

    valid_types = [
        "project",
        "work",
        "education",
        "award",
        "publication",
        "certification",
    ]
    if item_data.get("type") not in valid_types:
        return False, f"Invalid item type: {item_data.get('type')}"

    return True, ""


async def migrate_portfolio_items() -> Dict[str, str]:
    """Migrate portfolio items from legacy data to new database."""
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
    portfolio_item_repo = PortfolioItemRepository()

    # Load portfolio ID map and portfolio items data
    portfolio_id_map = load_portfolio_id_map()
    if not portfolio_id_map:
        logger.error("No portfolio ID map found, cannot migrate portfolio items")
        return {}

    portfolio_items_data = load_json_file("user_information.portfolio_items.json")
    if not portfolio_items_data:
        logger.error("No portfolio items data found")
        return {}

    # Map of old portfolio_item_id to new portfolio_item_id
    portfolio_item_id_map = {}
    migration_errors = []

    # Process each portfolio item with progress bar
    for item_data in tqdm(portfolio_items_data, desc="Migrating portfolio items"):
        try:
            # Validate portfolio item data
            is_valid, error_msg = validate_portfolio_item_data(item_data)
            if not is_valid:
                logger.warning(f"Invalid portfolio item data: {error_msg}")
                migration_errors.append(
                    {"portfolio_item": item_data.get("_id"), "error": error_msg}
                )
                continue

            portfolio_id = item_data["portfolio_id"]
            if portfolio_id not in portfolio_id_map:
                logger.warning(f"Portfolio ID not found in map: {portfolio_id}")
                continue

            new_portfolio_id = ObjectId(portfolio_id_map[portfolio_id])
            logger.debug(
                f"Processing portfolio item for portfolio: {portfolio_id} -> {new_portfolio_id}"
            )

            # Check if portfolio exists
            portfolio = await portfolio_repo.get_by_id(str(new_portfolio_id))
            if not portfolio:
                logger.warning(f"Portfolio not found: {new_portfolio_id}")
                continue

            # Check for existing portfolio item
            existing_items = await portfolio_item_repo.get_by_portfolio_id(
                str(new_portfolio_id)
            )
            if existing_items:
                for item in existing_items:
                    if item.title == item_data.get(
                        "title"
                    ) and item.type == item_data.get("type"):
                        logger.info(
                            f"Portfolio item already exists: {item.title} ({item.type})"
                        )
                        portfolio_item_id_map[
                            str(item_data.get("_id", {}).get("$oid", portfolio_id))
                        ] = str(item.id)
                        continue

            # Create a new portfolio item using the repository
            new_item = await portfolio_item_repo.create_item(
                portfolio_id=str(new_portfolio_id),
                title=str(item_data.get("title", "")),
                item_type=str(item_data.get("type", "")),
                description=str(item_data.get("description", "")),
                url=str(item_data.get("url", "")),
                bullet_points=[str(b) for b in item_data.get("bullet_points", []) if b],
                tags=[str(t) for t in item_data.get("tags", []) if t],
                date=str(item_data.get("date", "")),
                order=int(item_data.get("order", 0)),
                is_featured=bool(item_data.get("is_featured", False)),
                company=str(item_data.get("company", "")),
                location=str(item_data.get("location", "")),
            )

            # Update timestamps
            new_item.created_at = convert_mongo_date(item_data.get("created_at"))
            new_item.updated_at = convert_mongo_date(item_data.get("updated_at"))
            await new_item.save()

            logger.info(
                f"Created portfolio item: {new_item.title} ({new_item.type}) for portfolio: {portfolio_id}"
            )
            portfolio_item_id_map[
                str(item_data.get("_id", {}).get("$oid", portfolio_id))
            ] = str(new_item.id)

        except Exception as e:
            error_msg = f"Error migrating portfolio item for portfolio {item_data.get('portfolio_id')}: {e}"
            logger.error(error_msg)
            migration_errors.append(
                {"portfolio_item": item_data.get("_id"), "error": str(e)}
            )

    # Save the portfolio item ID map
    try:
        with open("portfolio_item_id_map.json", "w") as f:
            json.dump(portfolio_item_id_map, f, indent=2)
        logger.info(
            f"Saved portfolio item ID map with {len(portfolio_item_id_map)} mappings"
        )
    except Exception as e:
        logger.error(f"Error saving portfolio item ID map: {e}")

    # Save migration errors if any
    if migration_errors:
        try:
            with open("portfolio_items_migration_errors.json", "w") as f:
                json.dump(migration_errors, f, indent=2)
            logger.warning(
                f"Migration completed with {len(migration_errors)} errors. See portfolio_items_migration_errors.json for details."
            )
        except Exception as e:
            logger.error(f"Error saving migration errors: {e}")

    # Close the connection
    mongo_manager.close_async_connection()
    logger.info(
        f"Migration completed. Successfully migrated {len(portfolio_item_id_map)} portfolio items."
    )
    return portfolio_item_id_map


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
