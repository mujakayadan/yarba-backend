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

# Import the app directly to verify it works
from api.main import app


def main():
    """Run the FastAPI server optimized for Digital Ocean App Platform."""
    # Digital Ocean will provide PORT environment variable
    port = int(os.environ.get("PORT", "8000"))

    # Digital Ocean apps bind to 0.0.0.0
    host = "0.0.0.0"

    print(f"Starting API server at http://{host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        workers=1,
    )


if __name__ == "__main__":
    main()
