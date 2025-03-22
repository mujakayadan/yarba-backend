#!/usr/bin/env python
"""Helper script to run the API server with additional options."""

import argparse
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import uvicorn

from config.logging_config import configure_logging, get_logger
from config.settings import settings

# Configure logging
configure_logging()
logger = get_logger("api_runner")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run the FastAPI server")

    # Server options
    parser.add_argument(
        "--host",
        type=str,
        default=os.environ.get("HOST", "127.0.0.1"),
        help="Host to bind the server to",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", "8000")),
        help="Port to bind the server to",
    )
    parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--workers", type=int, default=1, help="Number of worker processes"
    )

    # Logging options
    parser.add_argument(
        "--log-level",
        type=str,
        default=(
            settings.logging.log_level.lower()
            if hasattr(settings.logging, "log_level")
            else "info"
        ),
        choices=["debug", "info", "warning", "error", "critical"],
        help="Logging level",
    )

    return parser.parse_args()


def main():
    """Run the FastAPI server."""
    args = parse_args()

    logger.info(f"Starting API server at http://{args.host}:{args.port}")
    logger.info(f"Documentation available at http://{args.host}:{args.port}/docs")

    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
