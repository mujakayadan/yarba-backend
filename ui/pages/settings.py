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
from core.llm.base import BaseLLM
from core.models.profile import Profile
from core.models.user import LLMPreferences, SectionPreferences

from ..components.model_selector import ModelSelector
from ..components.section_selector import SectionSelector

logger = get_logger(__name__)


class SettingsPage:
    """
    A class to handle the settings page functionality in the Streamlit application.

    This page allows users to configure:
    - LLM Configuration: AI model selection and parameters
    - User Preferences: Resume sections, life story, and formatting options
    - Feature Flags: System-wide feature toggles

    Args:
        model_selector (ModelSelector): Component for selecting AI models
    """

    def __init__(self, model_selector: ModelSelector) -> None:
        """Initialize SettingsPage with required components."""
        self.model_selector = model_selector
        self.section_selector = SectionSelector()

    def render(self) -> None:
        """Render the settings page with all configuration tabs."""
        st.title("⚙️ Settings")

        tab1, tab2, tab3 = st.tabs(
            ["LLM Configuration", "User Preferences", "Feature Flags"]
        )

        with tab1:
            self._render_llm_settings()

        with tab2:
            self._render_user_preferences()

        with tab3:
            self._render_feature_flags()

    def _render_llm_settings(self) -> None:
        """
        Render LLM configuration settings.

        Handles:
        - Model type selection
        - Model name selection
        - Temperature configuration
        """
        st.header("LLM Settings")

        # Get current settings from model selector
        model_type, model_name, temperature = self.model_selector.get_model_settings()

        # Model type selection
        model_type = st.selectbox(
            "Select Model Type",
            self.model_selector.model_types,
            index=self.model_selector.model_types.index(model_type),
            key="model_type_select",
        )

        # Model name selection based on type
        model_name = st.selectbox(
            "Select Model",
            self.model_selector.model_options[model_type],
            index=(
                self.model_selector.model_options[model_type].index(model_name)
                if model_name in self.model_selector.model_options[model_type]
                else 0
            ),
            key="model_name_select",
        )

        # Temperature slider
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=temperature,
            step=0.1,
            help="Higher values make the output more creative but less focused",
            key="temperature_slider",
        )

        if st.button("Save LLM Settings", key="save_llm_button"):
            self._save_llm_settings(model_type, model_name, temperature)

    def _save_llm_settings(
        self, model_type: str, model_name: str, temperature: float
    ) -> None:
        """
        Save LLM settings to database and update session state.

        Args:
            model_type: Selected model type
            model_name: Selected model name
            temperature: Selected temperature value
        """
        with get_unit_of_work() as uow:
            try:
                uow.users.update_llm_preferences(
                    st.session_state["user_id"],
                    {
                        "model_type": model_type,
                        "model_name": model_name,
                        "temperature": temperature,
                    },
                )
                # Update session state
                st.session_state["model_type"] = model_type
                st.session_state["model_name"] = model_name
                st.session_state["temperature"] = temperature

                st.success("✅ LLM settings saved successfully!")
                logger.info(
                    f"LLM preferences updated for user {st.session_state['user_id']}"
                )
            except Exception as e:
                logger.error(f"Failed to save LLM settings: {str(e)}")
                st.error(f"❌ Failed to save LLM settings: {str(e)}")

    def _render_user_preferences(self) -> None:
        """
        Render and handle user preferences section.

        This method handles:
        - Life story input
        - Resume section configurations
        - Section processing preferences
        - Saving preferences to database
        """
        st.header("User Preferences")

        # Life Story Section
        with st.expander("Life Story"):
            life_story = st.text_area(
                "Your Life Story",
                value="",
                height=200,
                help="This will be used to personalize your cover letter",
                key="life_story_input",
            )

        # Resume Section Preferences
        with st.expander("Resume Section Preferences"):
            # Projects
            st.subheader("Projects")
            max_projects = st.number_input(
                "Maximum Projects",
                min_value=1,
                max_value=10,
                value=5,
                key="max_projects_input",
            )
            bullet_points_per_project = st.number_input(
                "Bullet Points per Project",
                min_value=1,
                max_value=5,
                value=3,
                key="bullet_points_per_project_input",
            )

            # Work Experience
            st.subheader("Work Experience")
            max_jobs = st.number_input(
                "Maximum Jobs",
                min_value=1,
                max_value=10,
                value=5,
                key="max_jobs_input",
            )
            bullet_points_per_job = st.number_input(
                "Bullet Points per Job",
                min_value=1,
                max_value=5,
                value=3,
                key="bullet_points_per_job_input",
            )

            # Skills
            st.subheader("Skills")
            max_categories = st.number_input(
                "Maximum Skill Categories",
                min_value=1,
                max_value=10,
                value=5,
                key="max_categories_input",
            )
            min_skills = st.number_input(
                "Minimum Skills per Category",
                min_value=1,
                max_value=15,
                value=3,
                key="min_skills_input",
            )
            max_skills = st.number_input(
                "Maximum Skills per Category",
                min_value=1,
                max_value=15,
                value=7,
                key="max_skills_input",
            )

            # Career Summary
            st.subheader("Career Summary")
            min_words = st.number_input(
                "Minimum Words",
                min_value=10,
                max_value=50,
                value=25,
                key="min_words_input",
            )
            max_words = st.number_input(
                "Maximum Words",
                min_value=50,
                max_value=200,
                value=100,
                key="max_words_input",
            )

        # Section Processing Preferences
        with st.expander("Section Processing Preferences"):
            st.info(
                "Choose how each section should be processed during resume generation"
            )
            section_preferences = self.section_selector.get_user_section_selection()

        # Save button for all preferences
        if st.button("Save All Preferences", key="save_all_prefs_button"):
            # Prepare preferences data
            updated_preferences = {
                "project_details": {
                    "max_projects": max_projects,
                    "bullet_points_per_project": bullet_points_per_project,
                },
                "work_experience_details": {
                    "max_jobs": max_jobs,
                    "bullet_points_per_job": bullet_points_per_job,
                },
                "skills_details": {
                    "max_categories": max_categories,
                    "min_skills_per_category": min_skills,
                    "max_skills_per_category": max_skills,
                },
                "career_summary_details": {
                    "min_words": min_words,
                    "max_words": max_words,
                },
                "section_preferences": section_preferences,
            }

            # Save to session state for now
            st.session_state["user_preferences"] = updated_preferences
            st.session_state["life_story"] = life_story
            st.success("✅ Preferences saved successfully!")
            logger.info(f"Preferences updated for user {st.session_state['user_id']}")

    def _render_feature_flags(self) -> None:
        """
        Render and handle feature flags section.

        This section allows toggling system-wide features.
        """
        st.header("Feature Flags")
        st.info(
            "These settings control system-wide features. Changes affect all users."
        )

        # Get current feature flags from constants
        from config.constants import FEATURE_FLAGS

        # Create toggles for each feature flag
        updated_flags = {}

        # LinkedIn Integration
        linkedin_enabled = st.toggle(
            "LinkedIn Integration",
            value=FEATURE_FLAGS.get("linkedin_integration", True),
            help="Enable/disable LinkedIn job extraction",
        )
        updated_flags["linkedin_integration"] = linkedin_enabled

        # Clearance Check
        clearance_check = st.toggle(
            "Security Clearance Check",
            value=FEATURE_FLAGS.get("check_clearance", True),
            help="Check job descriptions for security clearance requirements",
        )
        updated_flags["check_clearance"] = clearance_check

        # PDF Preview
        pdf_preview = st.toggle(
            "PDF Preview",
            value=FEATURE_FLAGS.get("pdf_preview", True),
            help="Show PDF previews in the application",
        )
        updated_flags["pdf_preview"] = pdf_preview

        # Save button for feature flags
        if st.button("Save Feature Flags", key="save_flags_button"):
            try:
                # Save to session state for now
                st.session_state["feature_flags"] = updated_flags
                st.success("✅ Feature flags updated successfully!")
                logger.info("Feature flags updated")
            except Exception as e:
                logger.error(f"Failed to update feature flags: {str(e)}")
                st.error(f"❌ Failed to update feature flags: {str(e)}")
