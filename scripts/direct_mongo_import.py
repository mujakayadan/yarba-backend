#!/usr/bin/env python
"""
Direct MongoDB import script for migrating data from JSON files.

This script bypasses the Beanie ODM and directly uses PyMongo to import data.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bson import ObjectId
from pymongo import MongoClient

from config.logging_config import get_logger
from config.settings import settings

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


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for MongoDB documents."""

    def default(self, obj: Any) -> Any:
        """Handle MongoDB-specific types.

        Args:
            obj: Object to encode

        Returns:
            JSON-serializable object
        """
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)


async def import_json(
    client: MongoClient,
    collection_name: str,
    json_file: Path,
    drop_collection: bool = False,
) -> None:
    """Import JSON data into a MongoDB collection.

    Args:
        client: MongoDB client
        collection_name: Name of the collection to import into
        json_file: Path to the JSON file
        drop_collection: Whether to drop the collection before importing
    """
    try:
        # Get database and collection
        db = client[settings.mongodb_database]
        collection = db[collection_name]

        # Drop collection if requested
        if drop_collection:
            logger.info(f"Dropping collection: {collection_name}")
            await collection.drop()

        # Load JSON data
        logger.info(f"Loading data from {json_file}")
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Convert string IDs to ObjectIds if needed
        for item in data:
            if "_id" in item and isinstance(item["_id"], str):
                item["_id"] = ObjectId(item["_id"])

        # Insert data
        logger.info(f"Inserting {len(data)} documents into {collection_name}")
        if isinstance(data, list) and data:
            result = await collection.insert_many(data)
            logger.info(f"Inserted {len(result.inserted_ids)} documents")
        else:
            logger.warning(f"No data to insert into {collection_name}")

    except Exception as e:
        logger.error(f"Error importing data: {e}")


async def main(args: argparse.Namespace) -> None:
    """Main entry point.

    Args:
        args: Command line arguments
    """
    try:
        # Connect to MongoDB
        client = MongoClient(settings.mongodb_uri)
        logger.info(f"Connected to MongoDB at {settings.mongodb_uri}")

        # Import each specified file
        for mapping in args.mappings:
            try:
                collection, file_path = mapping.split(":")
                json_file = Path(file_path)
                if not json_file.exists():
                    logger.error(f"File does not exist: {json_file}")
                    continue

                await import_json(client, collection, json_file, args.drop_collections)
            except ValueError:
                logger.error(
                    f"Invalid mapping format: {mapping}. Use 'collection:file.json'"
                )

    except Exception as e:
        logger.error(f"Fatal error: {e}")


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Import JSON data into MongoDB collections"
    )
    parser.add_argument(
        "mappings",
        nargs="+",
        help="Collection to file mappings in the format 'collection:file.json'",
    )
    parser.add_argument(
        "--drop-collections",
        action="store_true",
        help="Drop collections before importing",
    )
    args = parser.parse_args()

    # Run the main function
    asyncio.run(main(args))
