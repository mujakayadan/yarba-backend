#!/usr/bin/env python
"""
Direct MongoDB import script for migrating data from JSON files.

This script bypasses the Beanie ODM and directly uses PyMongo to import data.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bson import ObjectId
from pymongo import MongoClient

from config.env_config import MONGODB_DATABASE, MONGODB_URI
from config.logging_config import get_logger

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = get_logger(__name__)

# Path to the data files
DATA_DIR = Path(__file__).parent.parent / "my_data"


def load_json_file(filename: str) -> List[Dict[str, Any]]:
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
        return []


def convert_mongo_dates(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB date objects to Python datetime objects."""
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            if "$date" in value:
                try:
                    result[key] = datetime.fromisoformat(
                        value["$date"].replace("Z", "+00:00")
                    )
                except ValueError:
                    # If conversion fails, keep the original value
                    result[key] = value
            else:
                result[key] = convert_mongo_dates(value)
        elif isinstance(value, list):
            result[key] = [
                convert_mongo_dates(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value
    return result


def convert_mongo_ids(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB ObjectId objects to strings."""
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            if "$oid" in value:
                result[key] = ObjectId(value["$oid"])
            else:
                result[key] = convert_mongo_ids(value)
        elif isinstance(value, list):
            result[key] = [
                convert_mongo_ids(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value
    return result


def prepare_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare a document for insertion by converting MongoDB types."""
    # First convert dates
    doc = convert_mongo_dates(doc)
    # Then convert ObjectIds
    doc = convert_mongo_ids(doc)
    return doc


def main():
    """Main function to import data directly into MongoDB."""
    logger.info("Starting direct MongoDB import")

    # Connect to MongoDB
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DATABASE]
    logger.info(f"Connected to MongoDB database: {MONGODB_DATABASE}")

    # Load data from JSON files
    users_data = load_json_file("user_information.users.json")
    profiles_data = load_json_file("user_information.profiles.json")
    portfolios_data = load_json_file("user_information.portfolio.json")

    # Import users
    user_id_map = {}  # Map of old _id to new _id
    users_collection = db["users"]

    for user_data in users_data:
        try:
            # Prepare the document
            user_doc = prepare_document(user_data)
            old_id = user_doc.pop("_id", None)

            # Check if user already exists
            existing_user = users_collection.find_one(
                {"username": user_doc.get("user_id")}
            )

            if existing_user:
                logger.info(f"User already exists: {user_doc.get('user_id')}")
                user_id_map[str(old_id)] = str(existing_user["_id"])
            else:
                # Rename user_id to username for new schema
                username = user_doc.pop("user_id", None)
                if username:
                    user_doc["username"] = username

                # Insert the user
                result = users_collection.insert_one(user_doc)
                logger.info(f"Inserted user: {username}, ID: {result.inserted_id}")

                if old_id:
                    user_id_map[str(old_id)] = str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error importing user: {e}")

    logger.info(f"Imported {len(user_id_map)} users")

    # Import profiles
    profiles_collection = db["profiles"]
    profile_id_map = {}  # Map of old _id to new _id

    for profile_data in profiles_data:
        try:
            # Prepare the document
            profile_doc = prepare_document(profile_data)
            old_id = profile_doc.pop("_id", None)
            old_user_id = profile_doc.get("user_id")

            # Find the corresponding user
            user = users_collection.find_one({"username": old_user_id})

            if not user:
                logger.warning(f"Skipping profile without valid user: {old_user_id}")
                continue

            # Update user_id to reference the new user
            profile_doc["user_id"] = str(user["_id"])

            # Rename personal_information to personal_info for new schema
            if "personal_information" in profile_doc:
                profile_doc["personal_info"] = profile_doc.pop("personal_information")

            # Check if profile already exists
            existing_profile = profiles_collection.find_one(
                {"user_id": profile_doc["user_id"]}
            )

            if existing_profile:
                logger.info(f"Profile already exists for user: {old_user_id}")
                profile_id_map[str(old_id)] = str(existing_profile["_id"])
            else:
                # Insert the profile
                result = profiles_collection.insert_one(profile_doc)
                logger.info(
                    f"Inserted profile for user: {old_user_id}, ID: {result.inserted_id}"
                )

                if old_id:
                    profile_id_map[str(old_id)] = str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error importing profile: {e}")

    logger.info(f"Imported {len(profile_id_map)} profiles")

    # Import portfolios
    portfolios_collection = db["portfolios"]
    portfolio_count = 0

    for portfolio_data in portfolios_data:
        try:
            # Prepare the document
            portfolio_doc = prepare_document(portfolio_data)
            old_id = portfolio_doc.pop("_id", None)
            old_user_id = portfolio_doc.get("user_id")

            # Find the corresponding user
            user = users_collection.find_one({"username": old_user_id})

            if not user:
                logger.warning(f"Skipping portfolio without valid user: {old_user_id}")
                continue

            # Update user_id to reference the new user
            portfolio_doc["user_id"] = str(user["_id"])

            # Check if portfolio already exists
            existing_portfolio = portfolios_collection.find_one(
                {"user_id": portfolio_doc["user_id"]}
            )

            if existing_portfolio:
                logger.info(f"Portfolio already exists for user: {old_user_id}")

                # Update the existing portfolio
                portfolios_collection.update_one(
                    {"_id": existing_portfolio["_id"]}, {"$set": portfolio_doc}
                )
                logger.info(f"Updated portfolio for user: {old_user_id}")
                portfolio_count += 1
            else:
                # Insert the portfolio
                result = portfolios_collection.insert_one(portfolio_doc)
                logger.info(
                    f"Inserted portfolio for user: {old_user_id}, ID: {result.inserted_id}"
                )
                portfolio_count += 1
        except Exception as e:
            logger.error(f"Error importing portfolio: {e}")

    logger.info(f"Imported {portfolio_count} portfolios")
    logger.info("Import completed")


if __name__ == "__main__":
    main()
