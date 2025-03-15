"""
Main entry point for the Resume Builder TeX application.

This module initializes and runs the Streamlit application.
"""

from config.logging_config import get_logger
from config.settings import Settings
from ui.streamlit_app import StreamlitApp

logger = get_logger(__name__)
settings = Settings()


def main():
    """Initialize and run the Streamlit application."""
    logger.info("Starting Resume Builder TeX application")
    app = StreamlitApp()
    app.run()


if __name__ == "__main__":
    main()
