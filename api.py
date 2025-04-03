#!/usr/bin/env python
"""API server runner for Digital Ocean App Platform."""

import logging
import os
import sys
from pathlib import Path

# Set up basic logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_runner_bootstrap")

# Add project root to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    logger.info(f"Adding {project_root} to Python path")
    sys.path.insert(0, project_root)

try:
    if os.path.exists("api"):
        logger.info(f"API directory contents: {os.listdir('api')}")
    else:
        logger.error("API directory not found!")

    import uvicorn

    # Try to import after debugging
    from config.logging_config import configure_logging, get_logger
    from config.settings import settings

    # Configure logging
    configure_logging()
    logger = get_logger("api_runner")

    def main():
        """Run the FastAPI server optimized for Digital Ocean App Platform."""
        # Digital Ocean will provide PORT environment variable
        port = int(os.environ.get("PORT", "8000"))

        # Digital Ocean apps bind to 0.0.0.0
        host = "0.0.0.0"

        logger.info(f"Starting API server at http://{host}:{port}")
        logger.info(f"Documentation available at http://{host}:{port}/docs")

        # Number of workers based on available CPUs
        workers = os.cpu_count() or 1

        try:
            # Verify we can import the app
            from api.main import app

            logger.info("Successfully imported app from api.main")

            uvicorn.run(
                "api.main:app",
                host=host,
                port=port,
                workers=workers,
                log_level=(
                    settings.logging.log_level.lower()
                    if hasattr(settings.logging, "log_level")
                    else "info"
                ),
            )
        except ImportError as e:
            logger.error(f"Failed to import app: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error running server: {e}")
            sys.exit(1)

    if __name__ == "__main__":
        main()

except Exception as e:
    logger.error(f"Bootstrap error: {e}")
    sys.exit(1)
