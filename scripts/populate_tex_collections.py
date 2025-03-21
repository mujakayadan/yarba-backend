"""Script to populate tex_headers and tex_templates collections from raw JSON data.

This script uses direct MongoDB commands without Beanie for maximum compatibility.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import motor.motor_asyncio
from bson import ObjectId

from config.env_config import MONGODB_DATABASE, MONGODB_URI
from config.logging_config import configure_logging

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

# Templates are complete document templates that include multiple sections
TEMPLATE_NAMES = [
    "muja_kayadan_resume",  # This is a full document template
]


async def connect_to_db():
    """Connect to MongoDB and return the database client.

    Returns:
        Tuple of (client, db)
    """
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
    db = client[MONGODB_DATABASE]
    return client, db


async def clear_collections(db):
    """Clear the tex_headers and tex_templates collections if they exist.

    Args:
        db: MongoDB database
    """
    # Clear collections if they exist
    if "tex_headers" in await db.list_collection_names():
        await db.tex_headers.delete_many({})
        logger.info("Cleared tex_headers collection")

    if "tex_templates" in await db.list_collection_names():
        await db.tex_templates.delete_many({})
        logger.info("Cleared tex_templates collection")


async def load_json_data() -> List[Dict[str, Any]]:
    """Load LaTeX data from the JSON file.

    Returns:
        List of LaTeX data entries from the JSON file
    """
    # Get the path to the JSON file
    base_dir = Path(__file__).resolve().parent.parent
    json_path = base_dir / "my_data" / "user_information.tex_headers.json"

    # Load the JSON data
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    logger.info(f"Loaded {len(data)} entries from JSON file")
    return data


async def migrate_to_tex_headers(db, data: List[Dict[str, Any]]):
    """Migrate appropriate entries to the tex_headers collection.

    Args:
        db: MongoDB database
        data: List of LaTeX data entries from the JSON file
    """
    headers_created = 0

    for item in data:
        # Skip items that are templates
        if item["name"] in TEMPLATE_NAMES:
            continue

        # Prepare document for insertion
        header_doc = {
            "name": item["name"],
            "content": item["content"],
            "category": "resume_section",  # Default category
            "is_default": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # Set more specific category based on name patterns
        if item["name"].endswith("_item"):
            header_doc["category"] = "resume_item"

        # Use original ID if available
        if "_id" in item and "$oid" in item["_id"]:
            header_doc["_id"] = ObjectId(item["_id"]["$oid"])

        try:
            # Insert document
            await db.tex_headers.insert_one(header_doc)
            headers_created += 1
        except Exception as e:
            logger.error(f"Error creating header {item['name']}: {str(e)}")

    logger.info(f"Created {headers_created} headers in tex_headers collection")


async def migrate_to_tex_templates(db, data: List[Dict[str, Any]]):
    """Migrate template entries to the tex_templates collection.

    Args:
        db: MongoDB database
        data: List of LaTeX data entries from the JSON file
    """
    templates_created = 0

    for item in data:
        # Only process items that are templates
        if item["name"] not in TEMPLATE_NAMES:
            continue

        # Prepare document for insertion
        template_doc = {
            "name": item["name"],
            "content": item["content"],
            "type": "resume",  # Default type
            "is_default": True,  # Make the templates default
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # Set more specific type if needed
        if "cover_letter" in item["name"]:
            template_doc["type"] = "cover_letter"

        # Use original ID if available
        if "_id" in item and "$oid" in item["_id"]:
            template_doc["_id"] = ObjectId(item["_id"]["$oid"])

        try:
            # Insert document
            await db.tex_templates.insert_one(template_doc)
            templates_created += 1
        except Exception as e:
            logger.error(f"Error creating template {item['name']}: {str(e)}")

    logger.info(f"Created {templates_created} templates in tex_templates collection")


async def main():
    """Main migration function."""
    logger.info("Starting migration of LaTeX data")

    # Connect to MongoDB
    client, db = await connect_to_db()

    try:
        # Clear collections
        await clear_collections(db)

        # Load data from JSON
        data = await load_json_data()

        # Migrate data to respective collections
        await migrate_to_tex_headers(db, data)
        await migrate_to_tex_templates(db, data)

        logger.info("Migration completed successfully")
    finally:
        # Close client connection
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
