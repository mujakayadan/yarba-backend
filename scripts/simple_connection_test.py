#!/usr/bin/env python
"""
Simple script to test MongoDB connection.
"""

import os
import sys
from pathlib import Path
import asyncio
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_connection():
    """Test MongoDB connection."""
    # Load environment variables
    load_dotenv()

    # Get MongoDB connection details from environment
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    database_name = os.getenv("MONGODB_DATABASE", "rbt")

    logger.info(f"Connecting to MongoDB at {mongo_uri}")

    try:
        # Create Motor client
        client = AsyncIOMotorClient(mongo_uri)

        # Test connection
        await client.admin.command("ping")
        logger.info("Successfully connected to MongoDB")

        # Get database
        db = client[database_name]

        # List collections
        collections = await db.list_collection_names()
        logger.info(f"Collections in {database_name} database: {collections}")

        return True
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return False


def main():
    """Run the script."""
    result = asyncio.run(test_connection())
    if result:
        logger.info("Connection test completed successfully")
    else:
        logger.error("Connection test failed")


if __name__ == "__main__":
    main()
