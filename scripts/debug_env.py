#!/usr/bin/env python
"""Script to debug environment variable loading."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add parent directory to path so we can import our application modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Explicitly load .env.local file
env_file_path = Path(__file__).parent.parent / ".env.local"
if env_file_path.exists():
    print(f"Loading environment from {env_file_path}")
    load_dotenv(dotenv_path=env_file_path)
else:
    print(f"Warning: {env_file_path} not found!")

from config.logging_config import get_logger
from config.settings import settings
from core.auth.firebase import FirebaseAuth

logger = get_logger(__name__)


def debug_env_variables():
    """Debug environment variable loading."""
    print("====== DEBUGGING ENVIRONMENT VARIABLES ======")
    logger.info("====== DEBUGGING ENVIRONMENT VARIABLES ======")

    # Direct environment access
    print("--- Direct environment variables ---")
    logger.info("--- Direct environment variables ---")
    env_vars = [
        "MONGODB_URI",
        "MONGODB_DATABASE",
        "FIREBASE_PROJECT_ID",
        "FIREBASE_PRIVATE_KEY",
        "FIREBASE_CLIENT_EMAIL",
    ]

    for var in env_vars:
        value = os.environ.get(var, "NOT SET")
        if var.endswith("KEY"):
            # Don't log actual key values
            print(f"{var}: {'SET' if value != 'NOT SET' else 'NOT SET'}")
            logger.info(f"{var}: {'SET' if value != 'NOT SET' else 'NOT SET'}")
        else:
            # Mask middle part of the value if it's a URI or long string
            if value != "NOT SET" and len(value) > 30:
                masked = value[:10] + "..." + value[-10:]
                print(f"{var}: {masked}")
                logger.info(f"{var}: {masked}")
            else:
                print(f"{var}: {value}")
                logger.info(f"{var}: {value}")

    # Settings access
    print("\n--- Settings values ---")
    logger.info("\n--- Settings values ---")
    print(f"settings.database.url: {settings.database.url}")
    logger.info(f"settings.database.url: {settings.database.url}")
    print(f"settings.database.name: {settings.database.name}")
    logger.info(f"settings.database.name: {settings.database.name}")
    print(f"settings.auth.firebase_project_id: {settings.auth.firebase_project_id}")
    logger.info(
        f"settings.auth.firebase_project_id: {settings.auth.firebase_project_id}"
    )
    print(f"settings.auth.firebase_client_email: {settings.auth.firebase_client_email}")
    logger.info(
        f"settings.auth.firebase_client_email: {settings.auth.firebase_client_email}"
    )
    print(
        f"settings.auth.firebase_private_key set: {bool(settings.auth.firebase_private_key)}"
    )
    logger.info(
        f"settings.auth.firebase_private_key set: {bool(settings.auth.firebase_private_key)}"
    )

    # Test Firebase initialization
    logger.info("\n--- Testing Firebase initialization ---")
    FirebaseAuth.debug_environment()

    result = FirebaseAuth.initialize()
    logger.info(f"Firebase initialization result: {result}")

    logger.info("====== END DEBUG ======")


if __name__ == "__main__":
    debug_env_variables()
