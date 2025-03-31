#!/usr/bin/env python
"""Beanie import script.

This script uses Beanie ODM to import data into MongoDB collections.
It's an alternative to direct_mongo_import.py that leverages the Beanie models.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

import motor.motor_asyncio
from beanie import Document, init_beanie
from pydantic import BaseModel

# Add parent directory to path to allow importing from the package
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.logging_config import get_logger
from config.settings import settings
from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.models.resume import Resume
from core.models.user import User

logger = get_logger(__name__)

# Map of collection names to document models
MODEL_MAP = {
    "users": User,
    "profiles": Profile,
    "portfolios": Portfolio,
    "resumes": Resume,
}


async def init_db() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    """Initialize the database connection.

    Returns:
        AsyncIOMotorDatabase: MongoDB database instance
    """
    # Connect to MongoDB
    client = motor.motor_asyncio.AsyncIOMotorClient(
        settings.mongodb_uri,
        maxPoolSize=settings.database.max_pool_size,
        minPoolSize=settings.database.min_pool_size,
    )
    db = client[settings.mongodb_database]

    # Initialize Beanie with all document models
    await init_beanie(
        database=db,
        document_models=list(MODEL_MAP.values()),
    )

    return db


async def import_json(
    collection_name: str,
    json_file: Path,
    drop_collection: bool = False,
) -> None:
    """Import JSON data into a collection using Beanie.

    Args:
        collection_name: Name of the collection to import into
        json_file: Path to the JSON file
        drop_collection: Whether to drop the collection before importing
    """
    try:
        # Check if we have a model for this collection
        if collection_name not in MODEL_MAP:
            logger.error(f"No model defined for collection {collection_name}")
            return

        # Get the document model
        model = MODEL_MAP[collection_name]

        # Load JSON data
        logger.info(f"Loading data from {json_file}")
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Drop collection if requested
        if drop_collection:
            logger.info(f"Dropping collection: {collection_name}")
            await model.get_motor_collection().drop()

        # Insert data
        logger.info(f"Inserting {len(data)} documents into {collection_name}")
        for item in data:
            try:
                # Create a document instance and save it
                doc = model.model_validate(item)
                await doc.save()
            except Exception as e:
                logger.error(f"Error inserting document: {e}")

        logger.info(f"Finished importing {collection_name}")

    except Exception as e:
        logger.error(f"Error importing data: {e}")


async def main(args: argparse.Namespace) -> None:
    """Main entry point.

    Args:
        args: Command line arguments
    """
    try:
        # Initialize database
        await init_db()

        # Import each specified file
        for mapping in args.mappings:
            try:
                collection, file_path = mapping.split(":")
                json_file = Path(file_path)
                if not json_file.exists():
                    logger.error(f"File does not exist: {json_file}")
                    continue

                await import_json(collection, json_file, args.drop_collections)
            except ValueError:
                logger.error(
                    f"Invalid mapping format: {mapping}. Use 'collection:file.json'"
                )

    except Exception as e:
        logger.error(f"Fatal error: {e}")


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Import JSON data into MongoDB collections using Beanie"
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
