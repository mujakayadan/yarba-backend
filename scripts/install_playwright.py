#!/usr/bin/env python3
"""
Script to install Playwright browser dependencies.
This should be run at least once before using Playwright in your application.
"""

import logging
import subprocess
import sys

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def install_playwright_browsers():
    """
    Install Playwright browser dependencies using the proper command for the current OS.
    """
    try:
        logger.info("Installing Playwright browser dependencies...")

        # Determine the appropriate command to run
        if sys.platform == "win32":
            # On Windows, use playwright install
            result = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "--with-deps"],
                check=True,
                capture_output=True,
                text=True,
            )
        else:
            # On Unix-like systems, use the direct install command
            result = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "--with-deps"],
                check=True,
                capture_output=True,
                text=True,
            )

        logger.info(f"Playwright installation stdout: {result.stdout}")
        if result.stderr:
            logger.warning(f"Playwright installation stderr: {result.stderr}")

        logger.info("Playwright browser dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install Playwright browser dependencies: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during Playwright installation: {e}")
        return False


if __name__ == "__main__":
    success = install_playwright_browsers()
    sys.exit(0 if success else 1)
