#!/usr/bin/env python
"""Script to migrate TeX data from JSON files to MongoDB collections."""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from pprint import pprint
from typing import Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorClient

# Add parent directory to path to allow importing from the package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


async def migrate_tex_data(
    client: AsyncIOMotorClient,
    data_dir: Path,
    clear_existing: bool = False,
) -> None:
    """Migrate TeX data from JSON files to MongoDB collections.

    Args:
        client: MongoDB client
        data_dir: Directory containing the JSON data files
        clear_existing: Whether to clear existing collections before migrating
    """
    # Get database
    db = client[settings.mongodb_database]

    # Define collections and corresponding JSON files
    collections = {
        "tex_headers": data_dir / "headers.json",
        "tex_templates": data_dir / "templates.json",
        "tex_preambles": data_dir / "preambles.json",
    }

    # Process each collection
    for collection_name, json_file in collections.items():
        if not json_file.exists():
            logger.warning(f"JSON file not found: {json_file}")
            continue

        collection = db[collection_name]

        # Clear existing documents if requested
        if clear_existing:
            logger.info(f"Clearing collection {collection_name}")
            await collection.delete_many({})

        # Load data from JSON file
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Error loading JSON file {json_file}: {e}")
            continue

        # Transform data to MongoDB documents
        documents = []
        for item in data:
            # Add required fields if missing
            if "name" not in item:
                item["name"] = f"untitled_{len(documents)}"
            if "description" not in item:
                item["description"] = f"No description for {item['name']}"
            documents.append(item)

        # Insert documents into collection
        if documents:
            logger.info(f"Inserting {len(documents)} documents into {collection_name}")
            result = await collection.insert_many(documents)
            logger.info(f"Inserted {len(result.inserted_ids)} documents")
        else:
            logger.warning(f"No documents to insert into {collection_name}")


async def main(args: argparse.Namespace) -> None:
    """Main entry point.

    Args:
        args: Command line arguments
    """
    # Connect to MongoDB
    try:
        client = AsyncIOMotorClient(settings.mongodb_uri)
        logger.info(f"Connected to MongoDB at {settings.mongodb_uri}")
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}")
        return

    # Migrate TeX data
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        return

    await migrate_tex_data(client, data_dir, args.clear_existing)


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Migrate TeX data to MongoDB")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/tex",
        help="Directory containing the JSON data files",
    )
    parser.add_argument(
        "--clear-existing",
        action="store_true",
        help="Clear existing collections before migrating",
    )
    args = parser.parse_args()

    # Run the main function
    asyncio.run(main(args))
