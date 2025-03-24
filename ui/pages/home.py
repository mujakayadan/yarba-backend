from enum import Enum, auto
from typing import Any, Dict, Optional

import streamlit as st

from config import APP_CONSTANTS, FEATURE_FLAGS, get_logger
from config.settings import settings
from core.database.connection import (
    get_async_database_connection,
    get_database_connection,
)
from core.database.factory import get_unit_of_work
from core.models.profile import Profile
from core.services.cover_letter_generation_service import CoverLetterGenerationService
from core.services.job_service import JobService
from core.services.latex_service import LatexService
from core.services.llm_service import LLMService
from core.services.prompt_service import PromptService
from core.services.resume_generation_service import ResumeGenerationService
from ui.components.section_selector import SectionSelector

logger = get_logger(__name__)


# Define document types locally since we deleted the generator module
class DocumentType(Enum):
    RESUME = auto()
    COVER_LETTER = auto()
    COMBINED = auto()


# Helper function to check clearance requirements in job descriptions
def check_clearance_requirement(job_description: str, clearance_keywords: list) -> bool:
    """
    Check if a job requires security clearance.

    Args:
        job_description: The job description text
        clearance_keywords: List of clearance-related keywords to check

    Returns:
        True if clearance is required, False otherwise
    """
    job_desc_lower = job_description.lower()
    for keyword in clearance_keywords:
        if keyword.lower() in job_desc_lower:
            return True
    return False


class HomePage:
    def __init__(
        self, model_selector, resume_generation_service, cover_letter_generation_service
    ):
        self.model_selector = model_selector
        self.resume_generation_service = resume_generation_service
        self.cover_letter_generation_service = cover_letter_generation_service
        self.section_selector = SectionSelector()
        # Initialize with default preferences
        self._load_user_preferences()

    def _load_user_preferences(self):
        """Load user preferences from database"""
        try:
            # Get the current user ID
            user_id = st.session_state.get("user_id")
            if not user_id:
                logger.warning("No user ID found in session state")
                self._set_default_preferences()
                return

            # Use synchronous database connection to avoid event loop issues
            from core.database.connection import get_database_connection

            # Get database connection
            db = get_database_connection()

            # Get profile directly from the database
            profile_data = db.profiles.find_one({"user_id": user_id})

            if profile_data and profile_data.get("preferences"):
                # Convert to Profile model
                profile = Profile.parse_obj(profile_data)

                # Set LLM preferences for service initialization
                if (
                    hasattr(profile.preferences, "llm_preferences")
                    and profile.preferences.llm_preferences
                ):
                    llm_prefs = profile.preferences.llm_preferences
                    # Store preferences to be used when generating
                    st.session_state["llm_preferences"] = {
                        "model_type": llm_prefs.get("model_type", "Claude"),
                        "model_name": llm_prefs.get(
                            "model_name", "claude-3-5-sonnet-20240620"
                        ),
                        "temperature": llm_prefs.get("temperature", 0.1),
                    }
                    logger.debug(f"Stored LLM preferences: {llm_prefs}")

                # Set section preferences
                if (
                    hasattr(profile.preferences, "section_preferences")
                    and profile.preferences.section_preferences
                ):
                    section_prefs = profile.preferences.section_preferences
                    st.session_state["section_preferences"] = section_prefs
                    logger.debug(f"Loaded section preferences: {section_prefs}")

                logger.debug("User preferences loaded successfully")
            else:
                logger.warning("No profile or preferences found for user")
                # Set default preferences
                self._set_default_preferences()
        except Exception as e:
            logger.error(f"Error loading user preferences: {e}")
            # Set default preferences if loading fails
            self._set_default_preferences()

    def _set_default_preferences(self):
        """Set default preferences when loading from database fails"""
        st.session_state["llm_preferences"] = {
            "model_type": "Claude",
            "model_name": "claude-3-5-sonnet-20240620",
            "temperature": 0.1,
        }
        logger.debug(
            "Using default model preferences: Claude/claude-3-5-sonnet-20240620/0.1"
        )

    def render(self):
        try:
            clearance_blocked = False
            job_info = None
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
                                        settings.linkedin_email,
                                        settings.linkedin_password,
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

                # Before the generation options, extract job info
                if job_description:
                    try:
                        # Create a temporary job service for job info extraction
                        async def extract_job_info():
                            # Get the unit of work
                            uow_generator = get_unit_of_work()
                            uow = await anext(uow_generator)
                            try:
                                profile_repo = uow.profile_repository
                                # Set up temporary LLM service
                                llm_service = LLMService(
                                    profile_repository=profile_repo,
                                )
                                # Set up prompt service
                                prompt_service = PromptService(
                                    user_repository=profile_repo
                                )
                                prompt_service.set_user_id(st.session_state["user_id"])

                                # Set up job service
                                job_service = JobService(
                                    llm_service=llm_service,
                                    prompt_service=prompt_service,
                                )

                                # Extract job info
                                job_info = await job_service.extract_job_info(
                                    job_description
                                )
                                return job_info
                            finally:
                                # Clean up
                                try:
                                    await uow_generator.aclose()
                                except Exception as e:
                                    logger.error(f"Error closing unit of work: {e}")

                        # Run the extraction
                        if "loop" in st.session_state:
                            job_info = st.session_state.loop.run_until_complete(
                                extract_job_info()
                            )
                            st.session_state["current_job_info"] = job_info
                    except Exception as e:
                        logger.error(f"Error extracting job info: {e}")
                        # Create a simple job info dict with defaults
                        job_info = {
                            "company_name": "Unknown Company",
                            "job_title": "Unknown Position",
                            "job_description": job_description,
                        }

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
                    # Get preferences from database
                    def _get_model_settings():
                        """Get model settings from the database using a synchronous connection."""
                        try:
                            # Get the current user ID
                            user_id = st.session_state.get("user_id")
                            if not user_id:
                                logger.warning("No user ID found in session state")
                                return None

                            # Use synchronous database connection to avoid event loop issues
                            from core.database.connection import get_database_connection
                            from core.models.profile import Profile

                            # Get database connection
                            db = get_database_connection()

                            # Get profile directly from the database
                            profile_data = db.profiles.find_one({"user_id": user_id})

                            if profile_data:
                                # Convert to Profile model
                                profile = Profile.parse_obj(profile_data)

                                if (
                                    profile.preferences
                                    and hasattr(profile.preferences, "llm_preferences")
                                    and profile.preferences.llm_preferences
                                ):
                                    llm_prefs = profile.preferences.llm_preferences
                                    return (
                                        llm_prefs.get("model_type", "Claude"),
                                        llm_prefs.get(
                                            "model_name", "claude-3-5-sonnet-20240620"
                                        ),
                                        llm_prefs.get("temperature", 0.1),
                                    )
                            return None
                        except Exception as e:
                            logger.error(f"Error getting model settings: {e}")
                            return None

                    # Get model settings
                    llm_settings = _get_model_settings()
                    if llm_settings:
                        model_type, model_name, temperature = llm_settings
                        st.text(f"Model Type: {model_type}")
                        st.text(f"Model: {model_name}")
                        st.text(f"Temperature: {temperature}")
                    else:
                        # Fallback to model_selector
                        model_type, model_name = self.model_selector.render()
                        temperature = 0.1  # Default temperature
                        st.text(f"Model Type: {model_type}")
                        st.text(f"Model: {model_name}")
                        st.text(f"Temperature: {temperature}")

                with st.expander("Section Settings"):
                    # Get section preferences from database or use section selector
                    section_prefs = st.session_state.get("section_preferences", {})

                    if (
                        section_prefs
                        and "sections_order" in section_prefs
                        and "visible_sections" in section_prefs
                    ):
                        # Use saved preferences
                        section_order = section_prefs.get("sections_order", [])
                        visible_sections = section_prefs.get("visible_sections", [])

                        # Display current section settings
                        st.subheader("Current Sections")
                        for section in section_order:
                            status = (
                                "✅ Included"
                                if section in visible_sections
                                else "❌ Excluded"
                            )
                            st.text(f"{section.replace('_', ' ').title()}: {status}")

                        # Convert to a format compatible with the generator
                        selected_sections = {}
                        for section in section_order:
                            if section in visible_sections:
                                selected_sections[section] = "process"
                            else:
                                selected_sections[section] = "skip"

                        # Store in session state for use during generation
                        st.session_state["section_preferences"] = selected_sections
                    else:
                        # Use section selector to get preferences
                        section_order, visible_sections = self.section_selector.render()

                        # Convert to a format compatible with the generator
                        selected_sections = {}
                        for section in section_order:
                            if section in visible_sections:
                                selected_sections[section] = "process"
                            else:
                                selected_sections[section] = "skip"

                        # Store in session state for use during generation
                        st.session_state["section_preferences"] = selected_sections

                        # Display current section settings
                        st.subheader("Current Sections")
                        for section in section_order:
                            status = (
                                "✅ Included"
                                if section in visible_sections
                                else "❌ Excluded"
                            )
                            st.text(f"{section.replace('_', ' ').title()}: {status}")

                st.markdown(
                    """
                    ℹ️ To change settings, use the Settings and Section Manager pages
                    from the sidebar navigation.
                """
                )

            # Handle generation when button is clicked
            if generate_button and job_description:
                with st.spinner("Generating your documents..."):
                    try:
                        # Map UI selection to DocumentType
                        doc_type = None
                        if generation_option == "Resume":
                            doc_type = DocumentType.RESUME
                        elif generation_option == "Cover Letter":
                            doc_type = DocumentType.COVER_LETTER
                        else:  # Both
                            doc_type = DocumentType.COMBINED

                        # Get or create the resume
                        resume_id = st.session_state.get("current_resume_id")
                        job_info = st.session_state.get("current_job_info")

                        if not resume_id:
                            # Create a new resume
                            async def create_resume():
                                # Get the unit of work
                                uow_generator = get_unit_of_work()
                                uow = await anext(uow_generator)
                                try:
                                    # Ensure user_id is a string
                                    user_id = str(st.session_state["user_id"])

                                    # Get user's profile
                                    profile = (
                                        await uow.profile_repository.get_by_user_id(
                                            user_id
                                        )
                                    )

                                    if not profile:
                                        raise ValueError(
                                            "Profile not found. Please create a profile first."
                                        )

                                    # Get user's portfolios
                                    portfolios = (
                                        await uow.portfolio_repository.get_by_user_id(
                                            user_id
                                        )
                                    )

                                    # Use first portfolio or create a new one
                                    if not portfolios:
                                        from core.models.portfolio import Portfolio

                                        # Create a default portfolio
                                        portfolio = Portfolio(
                                            user_id=user_id,
                                            title="Default Portfolio",
                                            description="Default portfolio created automatically",
                                        )
                                        await uow.portfolio_repository.create(portfolio)
                                        portfolio_id = portfolio.id
                                    else:
                                        portfolio_id = portfolios[0].id

                                    # Extract job info from session state
                                    job_info = st.session_state.get(
                                        "current_job_info", {}
                                    )
                                    company_name = job_info.get(
                                        "company_name", "unknown_company"
                                    )
                                    job_title = job_info.get(
                                        "job_title", "unknown_position"
                                    )

                                    # Create a new resume with all required fields
                                    from core.models.resume import Resume

                                    resume = Resume(
                                        user_id=user_id,
                                        profile_id=profile.id,
                                        portfolio_id=portfolio_id,
                                        job_description=job_description,
                                        # Make sure these required fields are not None
                                        company_name=company_name,
                                        job_title=job_title,
                                        resume_pdf=b"",  # Empty bytes for initial creation
                                        cover_letter_content="",  # Empty string for initial creation
                                        cover_letter_pdf=b"",  # Empty bytes for initial creation
                                    )

                                    await uow.resume_repository.create(resume)
                                    return str(resume.id)
                                finally:
                                    # Clean up
                                    try:
                                        await uow_generator.aclose()
                                    except Exception as e:
                                        logger.error(f"Error closing unit of work: {e}")

                            if "loop" in st.session_state:
                                resume_id = st.session_state.loop.run_until_complete(
                                    create_resume()
                                )
                                st.session_state["current_resume_id"] = resume_id
                            else:
                                st.error(
                                    "No event loop available. Cannot create resume."
                                )
                                return

                        # Configure and use generator service
                        async def generate_documents():
                            try:
                                # Ensure user_id is a string
                                user_id = str(st.session_state["user_id"])

                                # Get llm preferences from session state
                                llm_prefs = st.session_state.get(
                                    "llm_preferences",
                                    {
                                        "model_type": "Claude",
                                        "model_name": "claude-3-5-sonnet-20240620",
                                        "temperature": 0.1,
                                    },
                                )

                                # Initialize repositories and services
                                # Get the unit of work
                                uow_generator = get_unit_of_work()
                                uow = await anext(uow_generator)
                                try:
                                    # Configure services
                                    from core.services.prompt_service import (
                                        PromptService,
                                    )

                                    prompt_service = PromptService(
                                        user_repository=uow.profile_repository
                                    )
                                    prompt_service.set_user_id(user_id)

                                    llm_service = LLMService(
                                        profile_repository=uow.profile_repository,
                                        prompt_service=prompt_service,
                                        model=llm_prefs.get("model_name"),
                                        temperature=llm_prefs.get("temperature"),
                                    )
                                    # Configure LLM for the current user
                                    await llm_service.configure_for_user(user_id)

                                    latex_service = LatexService(
                                        preamble_repository=uow.preamble_repository,
                                        header_repository=uow.tex_header_repository,
                                        template_repository=uow.tex_template_repository,
                                    )

                                    # Configure generator service
                                    from core.services.resume_generation_service import (
                                        ResumeGenerationService,
                                    )

                                    resume_generation_service = ResumeGenerationService(
                                        resume_repository=uow.resume_repository,
                                        profile_repository=uow.profile_repository,
                                        portfolio_repository=uow.portfolio_repository,
                                        llm_service=llm_service,
                                        latex_service=latex_service,
                                    )

                                    # Apply section preferences if available
                                    section_prefs = st.session_state.get(
                                        "section_preferences", {}
                                    )

                                    # If job_info is available, use it
                                    company_name = job_info.get("company_name")
                                    job_title = job_info.get("job_title")

                                    # Generate the appropriate document type
                                    if doc_type == DocumentType.RESUME:
                                        result = await resume_generation_service.generate_resume(
                                            user_id=user_id,
                                            job_description=job_description,
                                            selected_sections=section_prefs,
                                            title=f"Resume for {company_name if company_name else 'Job Application'}",
                                            template_id="default",
                                            resume_id=resume_id if resume_id else None,
                                        )
                                        # Generate PDF
                                        pdf_content = await resume_generation_service.generate_pdf(
                                            resume_id=result.id,
                                            user_id=user_id,
                                        )
                                        return {"resume": result, "pdf": pdf_content}

                                    elif doc_type == DocumentType.COVER_LETTER:
                                        result = await self.cover_letter_generation_service.generate_cover_letter(
                                            user_id=user_id,
                                            job_description=job_description,
                                            title=f"Cover Letter for {company_name if company_name else 'Job Application'}",
                                            template_id="default",
                                            resume_id=resume_id if resume_id else None,
                                        )
                                        # Generate PDF
                                        pdf_content = await self.cover_letter_generation_service.generate_pdf(
                                            resume_id=result.id,
                                            user_id=user_id,
                                        )
                                        return {
                                            "cover_letter": result,
                                            "pdf": pdf_content,
                                        }

                                    else:  # Combined
                                        # Generate resume
                                        resume_result = await resume_generation_service.generate_resume(
                                            user_id=user_id,
                                            job_description=job_description,
                                            selected_sections=section_prefs,
                                            title=f"Resume for {company_name if company_name else 'Job Application'}",
                                            template_id="default",
                                            resume_id=resume_id if resume_id else None,
                                        )

                                        # Generate cover letter
                                        cover_letter_result = await self.cover_letter_generation_service.generate_cover_letter(
                                            user_id=user_id,
                                            job_description=job_description,
                                            title=f"Cover Letter for {company_name if company_name else 'Job Application'}",
                                            template_id="default",
                                        )

                                        # Generate PDFs
                                        resume_pdf = await resume_generation_service.generate_pdf(
                                            resume_id=resume_result.id,
                                            user_id=user_id,
                                        )

                                        cover_letter_pdf = await self.cover_letter_generation_service.generate_pdf(
                                            resume_id=cover_letter_result.id,
                                            user_id=user_id,
                                        )

                                        return {
                                            "resume": resume_result,
                                            "resume_pdf": resume_pdf,
                                            "cover_letter": cover_letter_result,
                                            "cover_letter_pdf": cover_letter_pdf,
                                        }
                                finally:
                                    # Clean up - close the unit of work generator
                                    try:
                                        await uow_generator.aclose()
                                    except Exception as e:
                                        logger.error(f"Error closing unit of work: {e}")
                            except Exception as e:
                                logger.error(
                                    f"Error in generate_documents: {e}", exc_info=True
                                )
                                return {"error": str(e)}

                        try:
                            if "loop" in st.session_state:
                                result = st.session_state.loop.run_until_complete(
                                    generate_documents()
                                )
                            else:
                                st.error(
                                    "No event loop available. Cannot generate documents."
                                )
                                return
                        except Exception as e:
                            st.error(f"Error during document generation: {str(e)}")
                            logger.error(
                                f"Exception in generate_documents: {e}", exc_info=True
                            )
                            return

                        # Check for errors
                        if "error" in result:
                            st.error(f"Generation failed: {result['error']}")
                            logger.error(
                                f"Document generation error: {result['error']}"
                            )
                        else:
                            st.success("Documents generated successfully!")

                            # Store the results for later reference
                            st.session_state["generation_result"] = result

                            # Show download buttons for PDFs
                            st.markdown("### Download Generated Documents")

                            # Prepare PDF data based on document type
                            if doc_type == DocumentType.RESUME:
                                # For resume only
                                resume_pdf = result.get("pdf")
                                if resume_pdf:
                                    st.download_button(
                                        label="📄 Download Resume PDF",
                                        data=resume_pdf,
                                        file_name="resume.pdf",
                                        mime="application/pdf",
                                        key="download_resume",
                                    )
                            elif doc_type == DocumentType.COVER_LETTER:
                                # For cover letter only
                                cover_letter_pdf = result.get("pdf")
                                if cover_letter_pdf:
                                    st.download_button(
                                        label="📝 Download Cover Letter PDF",
                                        data=cover_letter_pdf,
                                        file_name="cover_letter.pdf",
                                        mime="application/pdf",
                                        key="download_cover_letter",
                                    )
                            else:
                                # For combined (both resume and cover letter)
                                resume_pdf = result.get("resume_pdf")
                                cover_letter_pdf = result.get("cover_letter_pdf")

                                if resume_pdf:
                                    st.download_button(
                                        label="📄 Download Resume PDF",
                                        data=resume_pdf,
                                        file_name="resume.pdf",
                                        mime="application/pdf",
                                        key="download_resume",
                                    )

                                if cover_letter_pdf:
                                    st.download_button(
                                        label="📝 Download Cover Letter PDF",
                                        data=cover_letter_pdf,
                                        file_name="cover_letter.pdf",
                                        mime="application/pdf",
                                        key="download_cover_letter",
                                    )

                            # Show success message with balloons
                            st.balloons()

                    except Exception as e:
                        st.error(f"An error occurred during generation: {str(e)}")
                        logger.error(f"Document generation error: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error in home page: {str(e)}", exc_info=True)
            st.error(f"❌ An unexpected error occurred: {str(e)}")
