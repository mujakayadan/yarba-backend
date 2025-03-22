#!/usr/bin/env python
"""
Direct script to fix MongoDB validation schemas to handle NULL values.
This bypasses the migration framework.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import logging

from pymongo import MongoClient

from config.settings import settings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("fix_mongodb_schema")


def fix_mongodb_schema():
    """Fix MongoDB validation schemas to allow NULL values."""
    try:
        # Connect to MongoDB directly
        logger.info(f"Connecting to MongoDB at {settings.mongodb_uri}")
        client = MongoClient(settings.mongodb_uri)
        db = client[settings.mongodb_database]

        logger.info("Connected to MongoDB successfully")

        # Update User collection - allow null values for optional date fields
        logger.info("Updating users collection schema")
        db.command(
            {
                "collMod": "users",
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["username", "email", "hashed_password"],
                        "properties": {
                            "username": {"bsonType": "string"},
                            "email": {"bsonType": "string"},
                            "hashed_password": {"bsonType": "string"},
                            "is_active": {"bsonType": "bool"},
                            "is_superuser": {"bsonType": "bool"},
                            "email_verified": {"bsonType": "bool"},
                            "last_login": {"bsonType": ["date", "null"]},
                            "login_attempts": {"bsonType": "int"},
                            "account_locked_until": {"bsonType": ["date", "null"]},
                            "reset_password_token": {"bsonType": ["string", "null"]},
                            "reset_password_expires": {"bsonType": ["date", "null"]},
                            "verification_token": {"bsonType": ["string", "null"]},
                            "subscription_status": {"bsonType": "string"},
                            "subscription_expires": {"bsonType": ["date", "null"]},
                            "last_active": {"bsonType": ["date", "null"]},
                            "created_at": {"bsonType": "date"},
                            "updated_at": {"bsonType": "date"},
                        },
                    }
                },
            }
        )
        logger.info("Users collection schema updated successfully")

        # Update Profile collection - allow null values for optional string fields
        logger.info("Updating profiles collection schema")
        db.command(
            {
                "collMod": "profiles",
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["user_id", "full_name", "email"],
                        "properties": {
                            "user_id": {"bsonType": "objectId"},
                            "full_name": {"bsonType": "string"},
                            "email": {"bsonType": "string"},
                            "phone": {"bsonType": ["string", "null"]},
                            "address": {"bsonType": ["string", "null"]},
                            "city": {"bsonType": ["string", "null"]},
                            "state": {"bsonType": ["string", "null"]},
                            "zip_code": {"bsonType": ["string", "null"]},
                            "country": {"bsonType": ["string", "null"]},
                            "linkedin": {"bsonType": ["string", "null"]},
                            "github": {"bsonType": ["string", "null"]},
                            "website": {"bsonType": ["string", "null"]},
                            "signature": {"bsonType": ["binData", "null"]},
                            "life_story": {"bsonType": ["string", "null"]},
                            "preferences": {"bsonType": "object"},
                            "created_at": {"bsonType": "date"},
                            "updated_at": {"bsonType": "date"},
                        },
                    }
                },
            }
        )
        logger.info("Profiles collection schema updated successfully")

        logger.info("MongoDB schema fix completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Error fixing MongoDB schema: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = fix_mongodb_schema()
    sys.exit(0 if success else 1)
