"""Test script to verify API imports and configuration."""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.logging_config import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger("api_test")


async def test_api_imports():
    """Test API imports and verify FastAPI application setup."""
    try:
        logger.info("Testing API imports...")

        # Import FastAPI application
        from api.main import app

        logger.info(
            f"Successfully imported FastAPI application: {app.title} v{app.version}"
        )
        logger.info(f"OpenAPI URL: {app.openapi_url}")
        logger.info(f"Docs URL: {app.docs_url}")

        # Import and verify routers
        from api.routers import profiles

        logger.info(
            f"Successfully imported profiles router with {len(profiles.router.routes)} routes"
        )

        # Count total API endpoints
        total_routes = len(app.routes)
        logger.info(f"Total API endpoints: {total_routes}")

        # Test profile service dependency
        from api.dependencies.services import get_profile_service

        logger.info("Successfully imported profile service dependency")

        logger.info("All API imports are working correctly!")
        return True
    except Exception as e:
        logger.error(f"API import test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print(" API IMPORT TEST ".center(80, "="))
    print("=" * 80 + "\n")

    success = asyncio.run(test_api_imports())

    print("\n" + "=" * 80)
    if success:
        print(" API IMPORTS SUCCESSFUL ".center(80, "="))
    else:
        print(" API IMPORTS FAILED ".center(80, "="))
    print("=" * 80 + "\n")

    sys.exit(0 if success else 1)
