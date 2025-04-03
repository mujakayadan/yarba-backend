#!/usr/bin/env python
"""API server runner for Digital Ocean App Platform."""

import logging
import os
import sys
from pathlib import Path

# Configure basic logging first
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("api_runner")

# Add project root to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    logger.info(f"Added {project_root} to Python path")

try:
    import uvicorn

    # Import app directly
    from api.main import app

    logger.info("Successfully imported FastAPI app")

    def main():
        """Run the FastAPI server optimized for Digital Ocean App Platform."""
        # Get configuration from environment variables
        port = int(os.environ.get("PORT", "8000"))
        host = os.environ.get("HOST", "0.0.0.0")
        log_level = os.environ.get("LOG_LEVEL", "info")
        workers = int(os.environ.get("WORKERS", "1"))

        logger.info(f"Starting API server at http://{host}:{port}")
        logger.info(f"Workers: {workers}, Log level: {log_level}")

        # Run the application
        uvicorn.run(
            app,
            host=host,
            port=port,
            workers=workers,
            log_level=log_level,
        )

    if __name__ == "__main__":
        main()

except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)
except Exception as e:
    logger.error(f"Unexpected error during startup: {e}")
    sys.exit(1)
