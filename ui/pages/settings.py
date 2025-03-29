"""
Settings page module for managing user preferences and configurations.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import streamlit as st

from config import get_logger
from config.settings import settings
from core.database.factory import get_unit_of_work
from core.models.profile import Preferences, Profile
from ui.pages.home import DocumentType

from ..components.model_selector import ModelSelector
from ..components.section_selector import SectionSelector

logger = get_logger(__name__)


class SettingsPage:
    """
    A class to handle the settings page functionality in the Streamlit application.

    This page allows users to configure:
    - LLM Configuration: AI model selection and parameters
    - User Preferences: Resume sections, life story, and formatting options
    - Feature Flags: Enable/disable experimental features
    """

    def __init__(self) -> None:
        """Initialize the settings page."""
        self.model_selector = ModelSelector()

    def render(self) -> None:
        """Render the settings page with all configuration sections."""
        st.title("Settings")

        # Create tabs for different settings categories
        tabs = st.tabs(["AI Settings", "Resume Preferences", "Feature Flags"])

        with tabs[0]:
            self._render_llm_settings()

        with tabs[1]:
            self._render_user_preferences()

        with tabs[2]:
            self._render_feature_flags()

    def _render_llm_settings(self) -> None:
        """Render the LLM settings section."""
        st.header("AI Model Settings")
        st.write(
            "Configure the AI model used for generating content. "
            "Different models have different capabilities and performance characteristics."
        )

        # Get current profile
        profile = self._get_current_profile()
        if not profile:
            st.warning("Please create a profile first to save settings.")
            return

        # Get current LLM preferences
        llm_prefs = {}
        if profile.preferences and hasattr(profile.preferences, "llm_preferences"):
            llm_prefs = profile.preferences.llm_preferences or {}

        # Default values
        current_model_type = llm_prefs.get("model_type", "Claude")
        current_model_name = llm_prefs.get("model_name", "claude-3-5-sonnet-20240620")
        current_temperature = llm_prefs.get("temperature", 0.1)

        # Render model selector
        model_type, model_name = self.model_selector.render(
            current_model_type, current_model_name
        )

        # Temperature slider
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=float(current_temperature),
            step=0.1,
            help="Controls randomness: 0 is deterministic, 1 is very creative",
        )

        # Save button
        if st.button("Save AI Settings"):
            self._save_llm_settings(model_type, model_name, temperature)
            st.success("AI settings saved successfully!")

    def _save_llm_settings(
        self, model_type: str, model_name: str, temperature: float
    ) -> None:
        """
        Save LLM settings to the database.

        Args:
            model_type: The model type (e.g. OpenAI, Claude)
            model_name: The model name (e.g. gpt-4, claude-3-opus)
            temperature: The temperature (0.0-1.0)
        """
        try:
            # Get user ID from session state
            user_id = st.session_state.get("user_id")
            if not user_id:
                logger.warning("No user ID found in session state")
                st.error("No user ID found in session state")
                return

            # Get profile directly from MongoDB using synchronous client
            from pymongo import MongoClient

            from core.database.connection import get_database_connection
            from core.models.profile import Profile

            # Get database connection
            db = get_database_connection()

            # Get profile
            profile_data = db.profiles.find_one({"user_id": user_id})
            if not profile_data:
                st.error("No profile found for the current user")
                return

            # Parse profile
            profile = Profile.parse_obj(profile_data)

            # Update or create preferences
            if not profile.preferences:
                from core.models.profile import UserPreferences

                profile.preferences = UserPreferences()

            # Create LLM preferences dictionary
            llm_preferences = {
                "model_type": model_type,
                "model_name": model_name,
                "temperature": temperature,
            }

            # Update profile preferences
            profile.preferences.llm_preferences = llm_preferences

            # Save to database
            db.profiles.update_one(
                {"_id": profile.id},
                {"$set": {"preferences": profile.preferences.model_dump()}},
            )

            logger.debug(f"Saved LLM preferences: {llm_preferences}")
            st.success("✅ LLM settings saved successfully")

        except Exception as e:
            logger.error(f"Error saving LLM settings: {e}")
            st.error(f"An error occurred: {str(e)}")

    def _render_user_preferences(self) -> None:
        """Render the user preferences section."""
        st.header("Resume Preferences")
        st.write(
            "Configure your resume preferences, including which sections to include "
            "and how they should be ordered."
        )

        # Get current profile
        profile = self._get_current_profile()
        if not profile:
            st.warning("Please create a profile first to save settings.")
            return

        # Get current section preferences
        section_prefs = {}
        if profile.preferences and hasattr(profile.preferences, "section_preferences"):
            section_prefs = profile.preferences.section_preferences or {}

        # Default values for section preferences
        default_sections = [
            "personal_information",
            "career_summary",
            "work_experience",
            "education",
            "skills",
            "projects",
            "awards",
            "publications",
        ]

        current_sections_order = section_prefs.get("sections_order", default_sections)
        current_visible_sections = section_prefs.get(
            "visible_sections", default_sections[:6]
        )

        # Render section selector
        section_selector = SectionSelector(
            available_sections=default_sections,
            current_order=current_sections_order,
            current_visible=current_visible_sections,
        )
        sections_order, visible_sections = section_selector.render()

        # Other preferences
        st.subheader("Content Preferences")

        # Get current preferences
        work_exp_prefs = {}
        if profile.preferences and hasattr(profile.preferences, "work_experience"):
            work_exp_prefs = profile.preferences.work_experience or {}

        education_prefs = {}
        if profile.preferences and hasattr(profile.preferences, "education"):
            education_prefs = profile.preferences.education or {}

        skills_prefs = {}
        if profile.preferences and hasattr(profile.preferences, "skills"):
            skills_prefs = profile.preferences.skills or {}

        project_prefs = {}
        if profile.preferences and hasattr(profile.preferences, "project_details"):
            project_prefs = profile.preferences.project_details or {}

        # Work experience preferences
        st.write("Work Experience")
        col1, col2 = st.columns(2)
        with col1:
            show_work_desc = st.checkbox(
                "Show job descriptions",
                value=work_exp_prefs.get("show_description", True),
            )
        with col2:
            show_work_location = st.checkbox(
                "Show job locations",
                value=work_exp_prefs.get("show_location", True),
            )

        # Education preferences
        st.write("Education")
        col1, col2, col3 = st.columns(3)
        with col1:
            show_gpa = st.checkbox(
                "Show GPA",
                value=education_prefs.get("show_gpa", True),
            )
        with col2:
            show_courses = st.checkbox(
                "Show courses",
                value=education_prefs.get("show_courses", True),
            )
        with col3:
            show_edu_date = st.checkbox(
                "Show dates",
                value=education_prefs.get("show_date", True),
            )

        # Skills preferences
        st.write("Skills")
        col1, col2 = st.columns(2)
        with col1:
            show_skill_level = st.checkbox(
                "Show skill level",
                value=skills_prefs.get("show_level", True),
            )
        with col2:
            group_by_category = st.checkbox(
                "Group by category",
                value=skills_prefs.get("group_by_category", True),
            )

        # Project preferences
        st.write("Projects")
        col1, col2, col3 = st.columns(3)
        with col1:
            show_project_desc = st.checkbox(
                "Show descriptions",
                value=project_prefs.get("show_description", True),
            )
        with col2:
            show_project_url = st.checkbox(
                "Show URLs",
                value=project_prefs.get("show_url", True),
            )
        with col3:
            show_project_tech = st.checkbox(
                "Show technologies",
                value=project_prefs.get("show_technologies", True),
            )

        # Save button
        if st.button("Save Resume Preferences"):
            self._save_user_preferences(
                sections_order,
                visible_sections,
                {
                    "work_experience": {
                        "show_description": show_work_desc,
                        "show_location": show_work_location,
                        "show_date": True,  # Always show dates for work experience
                    },
                    "education": {
                        "show_gpa": show_gpa,
                        "show_courses": show_courses,
                        "show_date": show_edu_date,
                    },
                    "skills": {
                        "show_level": show_skill_level,
                        "group_by_category": group_by_category,
                    },
                    "project_details": {
                        "show_description": show_project_desc,
                        "show_url": show_project_url,
                        "show_technologies": show_project_tech,
                    },
                },
            )
            st.success("Resume preferences saved successfully!")

    def _save_user_preferences(
        self,
        sections_order: list,
        visible_sections: list,
        content_preferences: Dict[str, Dict[str, Any]],
    ) -> None:
        """
        Save user preferences to the database.

        Args:
            sections_order: List of section names in order
            visible_sections: List of visible section names
            content_preferences: Dictionary of content preferences by section
        """
        try:
            # Get user ID from session state
            user_id = st.session_state.get("user_id")
            if not user_id:
                logger.warning("No user ID found in session state")
                st.error("No user ID found in session state")
                return

            # Get profile directly from MongoDB using synchronous client
            from pymongo import MongoClient

            from core.database.connection import get_database_connection
            from core.models.profile import Profile

            # Get database connection
            db = get_database_connection()

            # Get profile
            profile_data = db.profiles.find_one({"user_id": user_id})
            if not profile_data:
                st.error("No profile found for the current user")
                return

            # Parse profile
            profile = Profile.parse_obj(profile_data)

            # Update or create preferences
            if not profile.preferences:
                from core.models.profile import UserPreferences

                profile.preferences = UserPreferences()

            # Create section preferences dictionary
            section_preferences = {
                "sections_order": sections_order,
                "visible_sections": visible_sections,
                "content_preferences": content_preferences,
            }

            # Update profile preferences
            profile.preferences.section_preferences = section_preferences

            # Save to database
            db.profiles.update_one(
                {"_id": profile.id},
                {"$set": {"preferences": profile.preferences.model_dump()}},
            )

            logger.debug(f"Saved section preferences: {section_preferences}")
            st.success("✅ User preferences saved successfully")

        except Exception as e:
            logger.error(f"Error saving user preferences: {e}")
            st.error(f"An error occurred: {str(e)}")

    def _render_feature_flags(self) -> None:
        """Render the feature flags section."""
        st.header("Feature Flags")
        st.write(
            "Enable or disable experimental features. "
            "These features may not be fully tested and could change in the future."
        )

        # Get current profile
        profile = self._get_current_profile()
        if not profile:
            st.warning("Please create a profile first to save settings.")
            return

        # Get current feature preferences
        feature_prefs = {}
        if profile.preferences and hasattr(profile.preferences, "feature_preferences"):
            feature_prefs = profile.preferences.feature_preferences or {}

        # Feature flags
        enable_ai_suggestions = st.checkbox(
            "Enable AI suggestions",
            value=feature_prefs.get("enable_ai_suggestions", True),
            help="Allow the AI to suggest improvements to your resume",
        )

        enable_auto_save = st.checkbox(
            "Enable auto-save",
            value=feature_prefs.get("enable_auto_save", True),
            help="Automatically save your work as you type",
        )

        enable_spell_check = st.checkbox(
            "Enable spell check",
            value=feature_prefs.get("enable_spell_check", True),
            help="Check spelling as you type",
        )

        enable_grammar_check = st.checkbox(
            "Enable grammar check",
            value=feature_prefs.get("enable_grammar_check", True),
            help="Check grammar as you type",
        )

        # Save button
        if st.button("Save Feature Flags"):
            self._save_feature_flags(
                enable_ai_suggestions,
                enable_auto_save,
                enable_spell_check,
                enable_grammar_check,
            )
            st.success("Feature flags saved successfully!")

    def _save_feature_flags(
        self,
        enable_ai_suggestions: bool,
        enable_auto_save: bool,
        enable_spell_check: bool,
        enable_grammar_check: bool,
    ) -> None:
        """
        Save feature flags to the database.

        Args:
            enable_ai_suggestions: Whether to enable AI suggestions
            enable_auto_save: Whether to enable auto save
            enable_spell_check: Whether to enable spell check
            enable_grammar_check: Whether to enable grammar check
        """
        try:
            # Get user ID from session state
            user_id = st.session_state.get("user_id")
            if not user_id:
                logger.warning("No user ID found in session state")
                st.error("No user ID found in session state")
                return

            # Get profile directly from MongoDB using synchronous client
            from pymongo import MongoClient

            from core.database.connection import get_database_connection
            from core.models.profile import Profile

            # Get database connection
            db = get_database_connection()

            # Get profile
            profile_data = db.profiles.find_one({"user_id": user_id})
            if not profile_data:
                st.error("No profile found for the current user")
                return

            # Parse profile
            profile = Profile.parse_obj(profile_data)

            # Update or create preferences
            if not profile.preferences:
                from core.models.profile import UserPreferences

                profile.preferences = UserPreferences()

            # Create feature flags dictionary
            feature_flags = {
                "enable_ai_suggestions": enable_ai_suggestions,
                "enable_auto_save": enable_auto_save,
                "enable_spell_check": enable_spell_check,
                "enable_grammar_check": enable_grammar_check,
            }

            # Update profile preferences
            profile.preferences.feature_flags = feature_flags

            # Save to database
            db.profiles.update_one(
                {"_id": profile.id},
                {"$set": {"preferences": profile.preferences.model_dump()}},
            )

            logger.debug(f"Saved feature flags: {feature_flags}")
            st.success("✅ Feature flags saved successfully")

        except Exception as e:
            logger.error(f"Error saving feature flags: {e}")
            st.error(f"An error occurred: {str(e)}")

    def _get_current_profile(self) -> Optional[Profile]:
        """
        Get the current user's profile.

        Returns:
            Optional[Profile]: The user's profile, or None if not found
        """
        # Check if we already have the profile in session state to avoid redundant DB calls
        if "current_profile" in st.session_state:
            return st.session_state.get("current_profile")

        profile = None
        try:
            # Get user ID from session state
            user_id = st.session_state.get("user_id")
            if not user_id:
                logger.warning("No user ID found in session state")
                return None

            # Get profile directly from MongoDB using synchronous client
            from core.database.connection import get_database_connection
            from core.models.profile import Profile

            # Get database connection
            db = get_database_connection()

            # Query the profile
            profile_data = db.profiles.find_one({"user_id": user_id})
            if profile_data:
                # Convert the MongoDB document to a Pydantic model
                profile = Profile.parse_obj(profile_data)
                # Store in session state for future use
                st.session_state["current_profile"] = profile
            else:
                logger.warning(f"No profile found for user ID: {user_id}")

        except Exception as e:
            logger.error(f"Error getting profile: {e}")
            st.error(f"Failed to load profile: {str(e)}")

        return profile
