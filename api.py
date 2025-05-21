#!/usr/bin/env python
"""API server runner for Digital Ocean App Platform."""

import os
import sys
from pathlib import Path

# Add project root to Python path first
project_root = str(Path(__file__).parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import uvicorn

from api.healthcheck import API_PRESENT, check_api_exists
from api.main import app
from config.logging_config import configure_logging, get_logger

# Import logging configuration from config
from config.settings import settings
from utils.text import sanitize_mongodb_uri

# Configure logging using settings
configure_logging()
logger = get_logger("api_runner")

# Debug environment variables
logger.info("==== Environment Variables ====")
logger.info(
    f"MONGODB_URI: {sanitize_mongodb_uri(os.environ.get('MONGODB_URI', 'Not set'))}"
)
logger.info(f"MONGODB_DATABASE: {os.environ.get('MONGODB_DATABASE', 'Not set')}")
logger.info(f"Settings database.url: {settings.database.url}")
logger.info(f"Settings database.name: {settings.database.name}")
logger.info("==== End Environment Variables ====")

logger.info(f"Project root: {project_root}")
logger.info(f"Python path: {sys.path}")

# Verify file structure
logger.info(f"Current directory contents: {os.listdir('.')}")
api_dir = Path(project_root) / "api"
if api_dir.exists():
    logger.info(f"API directory contents: {os.listdir(api_dir)}")

    # Check for the healthcheck file
    try:
        logger.info("Checking for healthcheck file...")
        logger.info(f"API_PRESENT: {API_PRESENT}")
        logger.info(f"API exists: {check_api_exists()}")
    except ImportError:
        logger.error("Failed to import healthcheck module")
else:
    logger.error(f"API directory not found at {api_dir}")
    sys.exit(1)

try:
    logger.info("Successfully imported uvicorn")

    # Try to import the FastAPI app
    logger.info("Attempting to import FastAPI app...")
    logger.info("Successfully imported FastAPI app")

    def main():
        """Run the FastAPI server optimized for Digital Ocean App Platform."""
        port = int(os.environ.get("PORT", "8000"))
        host = "0.0.0.0"

        logger.info(f"Starting API server at http://{host}:{port}")

        uvicorn.run(
            app,
            host=host,
            port=port,
            workers=1,
        )

    if __name__ == "__main__":
        main()

except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.error(f"Module search paths: {sys.path}")
    sys.exit(1)
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    sys.exit(1)
