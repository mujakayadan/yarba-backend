import streamlit as st

from config import (
    APP_CONSTANTS,
    FEATURE_FLAGS,
    LINKEDIN_EMAIL,
    LINKEDIN_PASSWORD,
    get_logger,
)
from config.settings import settings
from core.database.factory import get_unit_of_work
from core.generator.generator_manager import DocumentType
from core.generator.utils.job_analysis import check_clearance_requirement
from core.generator.utils.job_info import JobInfo
from core.generator.utils.output_manager import OutputManager
from ui.components.section_selector import SectionSelector

logger = get_logger(__name__)


class HomePage:
    def __init__(self, model_selector, generator_manager):
        self.model_selector = model_selector
        self.generator_manager = generator_manager
        self.section_selector = SectionSelector()
        # Initialize with default preferences
        self._initialize_preferences()

    def _initialize_preferences(self):
        """Initialize with default preferences."""
        try:
            # Set default preferences if loading fails
            self.model_selector.set_model_settings(
                model_type="Claude",
                model_name="claude-3-5-sonnet-20240620",
                temperature=0.1,
            )
            logger.debug("Initialized with default preferences")
        except Exception as e:
            logger.error(f"Error initializing preferences: {e}")

    def render(self):
        try:
            clearance_blocked = False
            left_col, right_col = st.columns([2, 1])

            with left_col:
                st.markdown("### 📋 Job Description")

                # Add tabs for different input methods
                input_tab1, input_tab2 = st.tabs(["📝 Manual Entry", "🔗 LinkedIn URL"])

                # Initialize job_description as None
                job_description = None

                with input_tab1:
                    manual_description = st.text_area(
                        "Enter the job description:",
                        height=200,
                        placeholder="Paste the job description here...",
                        help="Copy and paste the complete job description from the job posting",
                        key="manual_text_area",
                    )
                    if manual_description:
                        job_description = manual_description

                with input_tab2:
                    job_url = st.text_input(
                        "Enter LinkedIn job URL:",
                        placeholder="https://www.linkedin.com/jobs/...",
                        help="Enter the URL of the LinkedIn job posting",
                        key="url_input",
                    )
                    if job_url:
                        if not job_url.startswith("https://www.linkedin.com/"):
                            st.error(
                                "⚠️ Only LinkedIn job URLs are supported at this time."
                            )
                        else:
                            try:
                                # Initialize job extractor if needed
                                if not hasattr(self, "job_extractor"):
                                    from easy_applier.job_extractor import JobExtractor

                                    self.job_extractor = JobExtractor(
                                        LINKEDIN_EMAIL, LINKEDIN_PASSWORD
                                    )

                                url_description = str(
                                    self.job_extractor.extract_job_details(job_url)
                                )
                                job_description = url_description
                            except Exception as e:
                                st.error(f"Failed to extract job details: {str(e)}")
                                logger.error(f"LinkedIn extraction error: {e}")

                # Add clearance requirement check if feature is enabled
                if job_description and FEATURE_FLAGS["check_clearance"]:
                    clearance_required = check_clearance_requirement(
                        job_description, APP_CONSTANTS["clearance_keywords"]
                    )
                    if clearance_required:
                        logger.warning("Security clearance requirement detected")
                        st.error(
                            "🔒 This position requires security clearance. Generation will be disabled."
                        )
                        clearance_blocked = True

                st.markdown("### 🎯 Generation Options")
                generation_option = st.selectbox(
                    "What would you like to generate?",
                    ["Resume", "Cover Letter", "Both"],
                    format_func=lambda x: f"Generate {x}",
                )

                # Move generate button here, inside left column
                st.markdown(
                    "<div style='height: 20px;'></div>", unsafe_allow_html=True
                )  # Add some spacing
                generate_button = st.button(
                    (
                        "🚀 Generate"
                        if not clearance_blocked
                        else "🔒 Generation Disabled"
                    ),
                    use_container_width=True,
                    disabled=clearance_blocked,
                )

            with right_col:
                # Show current configuration (read-only)
                st.markdown("### ⚙️ Current Configuration")
                with st.expander("Model Settings"):
                    # Get model settings from model_selector
                    model_type, model_name, temperature = (
                        self.model_selector.get_model_settings()
                    )
                    st.text(f"Model Type: {model_type}")
                    st.text(f"Model: {model_name}")
                    st.text(f"Temperature: {temperature}")

                with st.expander("Section Settings"):
                    section_prefs = st.session_state.get("section_preferences", {})
                    if section_prefs:
                        for section, handling in section_prefs.items():
                            st.text(f"{section}: {handling}")
                    else:
                        # Get default sections from section_selector
                        default_sections = (
                            self.section_selector.get_user_section_selection()
                        )
                        for section, handling in default_sections.items():
                            st.text(f"{section}: {handling}")

                st.markdown(
                    """
                    ℹ️ To change settings, use the Settings and Section Manager pages 
                    from the sidebar navigation.
                """
                )

            # Handle generation when button is clicked
            if generate_button:
                self._handle_generation(
                    job_description,
                    generation_option,
                    st.session_state.get("section_preferences", {}),
                )

        except Exception as e:
            logger.error(f"Error in home page: {str(e)}", exc_info=True)
            st.error(f"❌ An unexpected error occurred: {str(e)}")

    def _handle_generation(self, job_description, generation_option, selected_sections):
        if not job_description:
            logger.warning("Generation attempted without job description")
            st.error("❌ Please enter a job description first.")
            return

        with st.spinner("🔄 Generating your documents..."):
            progress_bar = st.progress(0)
            status_area = st.empty()

            try:
                # Get job info
                job_info = JobInfo.extract_from_description(
                    job_description, self.generator_manager.llm_runner
                )

                # Create output manager directly
                output_manager = OutputManager(job_info)
                logger.info(f"Output manager working at: {output_manager.output_dir}")

                generation_type = DocumentType(
                    generation_option.lower().replace(" ", "_")
                )

                for result in self.generator_manager.generate(
                    generation_type=generation_type,
                    job_description=job_description,
                    selected_sections=selected_sections,
                    output_manager=output_manager,
                ):
                    if isinstance(result, tuple):
                        status_msg, progress = result
                        progress_bar.progress(progress)
                        status_area.text(status_msg)

                st.success("✨ Generation completed successfully!")
                st.balloons()
                logger.info("Generation completed successfully")
                st.success(f"Generation complete: {output_manager.output_dir}")

            except Exception as e:
                logger.error(f"Generation failed: {e}")
                st.error(f"❌ {str(e)}")
