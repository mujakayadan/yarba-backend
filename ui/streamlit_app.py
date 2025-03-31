"""Streamlit application implementation."""

import asyncio
from pathlib import Path
from typing import Any, Callable, Coroutine

import streamlit as st

from config.logging_config import get_logger
from config.settings import Settings
from core.database import (
    get_cover_letter_repository,
    get_portfolio_repository,
    get_preamble_repository,
    get_profile_repository,
    get_resume_repository,
    get_tex_header_repository,
)
from core.services.cover_letter_generation_service import CoverLetterGenerationService
from core.services.latex_service import LatexService
from core.services.llm_service import LLMService
from core.services.prompt_service import PromptService
from core.services.resume_generation_service import ResumeGenerationService
from ui.components.database_viewer import DatabaseViewer
from ui.components.model_selector import ModelSelector
from ui.pages.home import HomePage
from ui.pages.settings import SettingsPage

logger = get_logger(__name__)
settings = Settings()


def run_async(coro_func: Callable[[], Coroutine]) -> Any:
    """
    Run an async function in a Streamlit-safe way.

    Args:
        coro_func: A function that returns a coroutine when called

    Returns:
        The result of the coroutine
    """
    try:
        # Always create a new event loop to avoid reusing coroutines
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Call the function to get a fresh coroutine
            return loop.run_until_complete(coro_func())
        finally:
            # Clean up properly
            loop.close()
    except Exception as e:
        logger.error(f"Error running async function: {e}")
        raise


class StreamlitApp:
    """Streamlit Application for resume generator."""

    def __init__(self):
        """Initialize the application."""
        # Configure the page
        st.set_page_config(
            page_title="ResumeBuilder",
            page_icon="📝",
            layout="wide",
            initial_sidebar_state="expanded",
        )

        # Initialize database
        self._initialize_database()

        # Initialize services and components
        self._initialize_repositories_and_services()

        # Setup session state
        self.setup_session_state()

        # Load CSS
        self._load_css()

        # Create pages
        self.home_page = HomePage(
            self.model_selector,
            self.resume_generation_service,
            self.cover_letter_generation_service,
        )
        self.settings_page = SettingsPage()
        self.database_viewer = DatabaseViewer()

        if "components_initialized" not in st.session_state:
            self._store_components()
            st.session_state["components_initialized"] = True

    def _initialize_repositories_and_services(self):
        """Initialize repositories and services"""
        try:
            # Initialize repositories using async functions
            def get_repo_from_generator(gen):
                """Helper to get first yield from generator"""
                try:
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        # Create a new event loop if there isn't one available
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    gen_instance = gen.__aiter__()
                    return loop.run_until_complete(gen_instance.__anext__())
                except Exception as e:
                    logger.error(f"Error getting repository from generator: {e}")
                    raise

            # Initialize all repositories
            self.resume_repository = get_repo_from_generator(get_resume_repository())
            self.profile_repository = get_repo_from_generator(get_profile_repository())
            self.portfolio_repository = get_repo_from_generator(
                get_portfolio_repository()
            )
            self.cover_letter_repository = get_repo_from_generator(
                get_cover_letter_repository()
            )
            preamble_repository = get_repo_from_generator(get_preamble_repository())
            tex_header_repository = get_repo_from_generator(get_tex_header_repository())

            # Create dependent services
            self.prompt_service = PromptService()
            self.llm_service = LLMService(
                profile_repository=self.profile_repository,
                prompt_service=self.prompt_service,
            )

            self.latex_service = LatexService(
                preamble_repository=preamble_repository,
                header_repository=tex_header_repository,
            )

            # Initialize generation services
            self.resume_generation_service = ResumeGenerationService(
                resume_repository=self.resume_repository,
                profile_repository=self.profile_repository,
                portfolio_repository=self.portfolio_repository,
                llm_service=self.llm_service,
                latex_service=self.latex_service,
            )

            self.cover_letter_generation_service = CoverLetterGenerationService(
                cover_letter_repository=self.cover_letter_repository,
                resume_repository=self.resume_repository,
                profile_repository=self.profile_repository,
                portfolio_repository=self.portfolio_repository,
                llm_service=self.llm_service,
                latex_service=self.latex_service,
            )

            # Initialize components
            self.model_selector = ModelSelector()

            logger.info("Repositories and services initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing repositories and services: {e}")
            st.error(f"Failed to initialize application services: {str(e)}")
            st.stop()

    def _initialize_database(self):
        """Initialize the database connection."""
        # Create an event loop for the app
        if "loop" not in st.session_state:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                st.session_state["loop"] = loop

                # Initialize Beanie with document models
                from beanie import init_beanie

                from core.database.connection import get_async_database_connection
                from core.models.cover_letter import CoverLetter
                from core.models.portfolio import Portfolio
                from core.models.preamble import Preamble
                from core.models.profile import Profile
                from core.models.resume import Resume
                from core.models.tex_header import TexHeader

                # Import models that need to be registered with Beanie
                from core.models.user import User

                # Get database and initialize Beanie
                async def initialize_beanie():
                    db = await get_async_database_connection()
                    await init_beanie(
                        database=db,
                        document_models=[
                            User,
                            Profile,
                            Portfolio,
                            Resume,
                            CoverLetter,
                            Preamble,
                            TexHeader,
                        ],
                    )
                    return db

                db = loop.run_until_complete(initialize_beanie())
                st.session_state["db"] = db
                logger.info("Database initialized with Beanie ODM for Streamlit app")
            except Exception as e:
                logger.error(f"Failed to initialize database: {e}")
                st.error(f"Failed to initialize database: {str(e)}")
                st.stop()

    def _store_components(self):
        """Store UI components in session state"""
        st.session_state["settings"] = settings
        st.session_state["model_selector"] = self.model_selector
        st.session_state["resume_generation_service"] = self.resume_generation_service
        st.session_state["cover_letter_generation_service"] = (
            self.cover_letter_generation_service
        )
        st.session_state["profile_repository"] = self.profile_repository
        st.session_state["portfolio_repository"] = self.portfolio_repository
        st.session_state["resume_repository"] = self.resume_repository
        st.session_state["llm_service"] = self.llm_service

    def setup_session_state(self):
        """Initialize session state variables"""
        if "user_id" not in st.session_state:
            # Use the test_user_id directly from settings
            # It should already be a PydanticObjectId thanks to the validator
            user_id = settings.test_user_id
            logger.debug(f"Using test_user_id from settings: {user_id}")
            st.session_state["user_id"] = user_id
        else:
            logger.debug(
                f"Current user_id in session state: {st.session_state['user_id']}"
            )

        # Initialize other session state variables
        if "portfolio_initialized" not in st.session_state:
            st.session_state["portfolio_initialized"] = False
        if "current_page" not in st.session_state:
            st.session_state["current_page"] = "home"

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

            # Navigation using buttons
            st.subheader("Navigation")

            if st.button("🏠 Home", key="nav_home", use_container_width=True):
                st.session_state["current_page"] = "home"
                st.rerun()

            if st.button("⚙️ Settings", key="nav_settings", use_container_width=True):
                st.session_state["current_page"] = "settings"
                st.rerun()

            if st.button("🗄️ Database", key="nav_database", use_container_width=True):
                st.session_state["current_page"] = "database"
                st.rerun()

        # Render selected page
        current_page = st.session_state["current_page"]

        if current_page == "home":
            self.home_page.render()
        elif current_page == "settings":
            self.settings_page.render()
        elif current_page == "database":
            self.database_viewer.render()


if __name__ == "__main__":
    app = StreamlitApp()
    app.run()
