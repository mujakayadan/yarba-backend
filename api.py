#!/usr/bin/env python
"""API server runner for Digital Ocean App Platform."""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import uvicorn

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


if __name__ == "__main__":
    main()
