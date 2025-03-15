"""Streamlit application implementation."""

import logging
import asyncio
from pathlib import Path

import streamlit as st

from config.logging_config import get_logger
from config.settings import Settings
from core.generator.generator_manager import GeneratorManager
from core.database import init_db
from ui.components.database_viewer import DatabaseViewer
from ui.components.model_selector import ModelSelector
from ui.pages.home import HomePage
from ui.pages.settings import SettingsPage

logger = get_logger(__name__)
settings = Settings()


@st.cache_resource
async def initialize_app_database():
    """Initialize the database connection for the Streamlit app."""
    try:
        await init_db()
        logger.info("Database initialized for Streamlit app")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


class StreamlitApp:
    def __init__(self):
        # Configure the page
        st.set_page_config(
            page_title=settings.ui.title,
            page_icon=settings.ui.page_icon,
            layout=settings.ui.layout_type,
            initial_sidebar_state=settings.ui.initial_sidebar_state,
        )

        # Load and apply CSS
        self._load_css()

        # Initialize session state first - Call it explicitly
        self.setup_session_state()

        # Initialize database
        if not asyncio.run(initialize_app_database()):
            st.error(
                "Failed to initialize database. Please check your database connection."
            )
            st.stop()

        # Initialize components after database is ready
        self.model_selector = ModelSelector()
        self.generator_manager = GeneratorManager(st.session_state["user_id"])

        # Initialize pages
        self.home_page = HomePage(self.model_selector, self.generator_manager)
        self.settings_page = SettingsPage(self.model_selector)

        if "components_initialized" not in st.session_state:
            self._store_components()
            st.session_state["components_initialized"] = True

    def _store_components(self):
        """Store components in session state"""
        st.session_state["model_selector"] = self.model_selector
        st.session_state["generator_manager"] = self.generator_manager
        logger.debug("Components stored in session state")

    def setup_session_state(self):
        """Initialize session state variables"""
        if "user_id" not in st.session_state:
            logger.debug(
                f"Setting user_id in session state to: {settings.test_user_id}"
            )
            st.session_state["user_id"] = settings.test_user_id
        else:
            logger.debug(
                f"Current user_id in session state: {st.session_state['user_id']}"
            )
        if "portfolio_initialized" not in st.session_state:
            st.session_state["portfolio_initialized"] = False

    def _load_css(self):
        css_file = Path(__file__).parent / "static" / "styles.css"
        with open(css_file) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    def run(self):
        logger.info("Starting StreamlitApp")
        st.title(settings.ui.title)

        # Sidebar navigation
        with st.sidebar:
            # Center the logo
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                try:
                    ico_path = Path(__file__).parent / "static" / "ico" / "ico.png"
                    if ico_path.exists():
                        with open(ico_path, "rb") as f:
                            image_data = f.read()
                        st.image(image_data, width=80)
                except Exception as e:
                    logger.error(f"Error loading icon: {e}")
                    st.markdown("")

            # Navigation menu using buttons
            if "current_page" not in st.session_state:
                st.session_state.current_page = "home"

            # Navigation buttons
            if st.button("🏠 Home", key="nav_home", use_container_width=True):
                st.session_state.current_page = "home"

            if st.button("⚙️ Settings", key="nav_settings", use_container_width=True):
                st.session_state.current_page = "settings"

            if st.button("🗄️ Database", key="nav_database", use_container_width=True):
                st.session_state.current_page = "database"

        # Render selected page
        if st.session_state.current_page == "home":
            self.home_page.render()
        elif st.session_state.current_page == "settings":
            self.settings_page.render()
        else:
            DatabaseViewer().render()


if __name__ == "__main__":
    app = StreamlitApp()
    app.run()
