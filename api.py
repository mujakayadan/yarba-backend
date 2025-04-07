#!/usr/bin/env python
"""API server runner for Digital Ocean App Platform."""

import logging
import os
import sys
from pathlib import Path

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("api_runner")

# Add project root to Python path
project_root = str(Path(__file__).parent.absolute())
logger.info(f"Project root: {project_root}")
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    logger.info(f"Added {project_root} to Python path")

# Print Python path for debugging
logger.info(f"Python path: {sys.path}")

# Verify file structure
logger.info(f"Current directory contents: {os.listdir('.')}")
api_dir = Path(project_root) / "api"
if api_dir.exists():
    logger.info(f"API directory contents: {os.listdir(api_dir)}")
else:
    logger.error(f"API directory not found at {api_dir}")
    sys.exit(1)

try:
    import uvicorn

    logger.info("Successfully imported uvicorn")

    # Try to import the FastAPI app
    logger.info("Attempting to import FastAPI app...")
    from api.main import app

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
