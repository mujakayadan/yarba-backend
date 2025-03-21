#!/usr/bin/env python
"""Script to populate TeX collections in the database."""

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


async def populate_collection(
    client: AsyncIOMotorClient,
    collection_name: str,
    data_file: Path,
    clear_existing: bool = False,
) -> None:
    """Populate a collection with data from a JSON file.

    Args:
        client: MongoDB client
        collection_name: Name of the collection to populate
        data_file: Path to the JSON file containing the data
        clear_existing: Whether to clear the existing collection before populating
    """
    # Get database and collection
    db = client[settings.mongodb_database]
    collection = db[collection_name]

    # Clear existing documents if requested
    if clear_existing:
        logger.info(f"Clearing collection {collection_name}")
        await collection.delete_many({})

    # Read and parse the JSON file
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error loading data file {data_file}: {e}")
        return

    # Insert the documents
    if isinstance(data, list):
        if not data:
            logger.warning(f"No documents found in {data_file}")
            return

        # Make sure each document has a name field
        for doc in data:
            if "name" not in doc:
                logger.error(f"Document missing 'name' field: {doc}")
                return

        # Insert the documents
        logger.info(f"Inserting {len(data)} documents into {collection_name}")
        await collection.insert_many(data)
        logger.info(
            f"Successfully inserted {len(data)} documents into {collection_name}"
        )
    else:
        logger.error(f"Data in {data_file} is not a list")


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

    # Populate the collections
    base_dir = Path(args.data_dir)

    # Map of collection names to data files
    collections = {
        "tex_headers": base_dir / "tex_headers.json",
        "tex_templates": base_dir / "tex_templates.json",
        "tex_preambles": base_dir / "tex_preambles.json",
    }

    # Validate data files
    for collection, file_path in collections.items():
        if not file_path.exists():
            logger.error(f"Data file not found: {file_path}")
            return

    # Populate the collections
    for collection, file_path in collections.items():
        await populate_collection(client, collection, file_path, args.clear_existing)


if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Populate TeX collections in the database"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/tex",
        help="Directory containing the JSON data files",
    )
    parser.add_argument(
        "--clear-existing",
        action="store_true",
        help="Clear existing collections before populating",
    )

    args = parser.parse_args()

    # Run the main function
    asyncio.run(main(args))
