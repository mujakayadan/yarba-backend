"""Script to migrate LaTeX data from user_information.tex_headers.json to dedicated collections.

This script loads data from the JSON file and populates:
1. tex_headers collection - For section headers, item templates, etc.
2. tex_templates collection - For full document templates (muja_kayadan_resume, etc.)
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
from pymongo.errors import DuplicateKeyError

from config.env_config import MONGODB_DATABASE, MONGODB_URI
from config.logging_config import configure_logging
from core.models.tex_header import TexHeader
from core.models.tex_template import TexTemplate

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

# Templates are complete document templates that include multiple sections
TEMPLATE_NAMES = [
    "muja_kayadan_resume",  # This is a full document template
]


async def init_beanie():
    """Initialize Beanie ODM."""
    from beanie import init_beanie
    from motor.motor_asyncio import AsyncIOMotorClient

    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[MONGODB_DATABASE]

    # Initialize beanie with our document models
    await init_beanie(
        database=db,
        document_models=[
            TexHeader,
            TexTemplate,
        ],
    )


async def clear_collections():
    """Clear the tex_headers and tex_templates collections if they exist."""
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
    db = client[MONGODB_DATABASE]

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


async def migrate_to_tex_headers(data: List[Dict[str, Any]]):
    """Migrate appropriate entries to the tex_headers collection.

    Args:
        data: List of LaTeX data entries from the JSON file
    """
    headers_created = 0

    for item in data:
        # Skip items that are templates
        if item["name"] in TEMPLATE_NAMES:
            continue

        # Create a TexHeader for each item
        try:
            header = TexHeader(
                id=(
                    ObjectId(item["_id"]["$oid"])
                    if "_id" in item and "$oid" in item["_id"]
                    else None
                ),
                name=item["name"],
                content=item["content"],
                category="resume_section",  # Default category
                is_default=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            # Set more specific category based on name patterns
            if item["name"].endswith("_item"):
                header.category = "resume_item"

            await header.create()
            headers_created += 1

        except DuplicateKeyError:
            logger.warning(f"Duplicate key for header: {item['name']}")
        except Exception as e:
            logger.error(f"Error creating header {item['name']}: {str(e)}")

    logger.info(f"Created {headers_created} headers in tex_headers collection")


async def migrate_to_tex_templates(data: List[Dict[str, Any]]):
    """Migrate template entries to the tex_templates collection.

    Args:
        data: List of LaTeX data entries from the JSON file
    """
    templates_created = 0

    for item in data:
        # Only process items that are templates
        if item["name"] not in TEMPLATE_NAMES:
            continue

        # Create a TexTemplate for each template
        try:
            template = TexTemplate(
                id=(
                    ObjectId(item["_id"]["$oid"])
                    if "_id" in item and "$oid" in item["_id"]
                    else None
                ),
                name=item["name"],
                content=item["content"],
                type="resume",  # Default type
                is_default=True,  # Make the templates default
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            # Set more specific type if needed
            if "cover_letter" in item["name"]:
                template.type = "cover_letter"

            await template.create()
            templates_created += 1

        except DuplicateKeyError:
            logger.warning(f"Duplicate key for template: {item['name']}")
        except Exception as e:
            logger.error(f"Error creating template {item['name']}: {str(e)}")

    logger.info(f"Created {templates_created} templates in tex_templates collection")


async def main():
    """Main migration function."""
    logger.info("Starting migration of LaTeX data")

    # Initialize Beanie
    await init_beanie()

    # Clear collections
    await clear_collections()

    # Load data from JSON
    data = await load_json_data()

    # Migrate data to respective collections
    await migrate_to_tex_headers(data)
    await migrate_to_tex_templates(data)

    logger.info("Migration completed successfully")


if __name__ == "__main__":
    asyncio.run(main())
