"""Example demonstrating how to use the resume services with Streamlit."""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st
from bson import ObjectId

# Make sure we can import from the project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config.logging_config import get_logger
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.profile_repository import ProfileRepository
from core.repositories.resume_repository import ResumeRepository
from core.repositories.tex_header_repository import TexHeaderRepository
from core.repositories.tex_template_repository import TexTemplateRepository
from core.services.llm_service import LLMService
from core.services.prompt_service import PromptService
from core.services.resume_generation_service import ResumeGenerationService
from core.services.tex_service import TexService

# Set up logger
logger = get_logger(__name__)

# Initialize services
portfolio_repository = PortfolioRepository()
profile_repository = ProfileRepository()
resume_repository = ResumeRepository()
tex_template_repository = TexTemplateRepository()
tex_header_repository = TexHeaderRepository()

prompt_service = PromptService()
llm_service = LLMService(
    profile_repository=profile_repository, prompt_service=prompt_service
)
tex_service = TexService(
    tex_template_repository=tex_template_repository,
    tex_header_repository=tex_header_repository,
)

resume_service = ResumeGenerationService(
    resume_repository=resume_repository,
    portfolio_repository=portfolio_repository,
    profile_repository=profile_repository,
    llm_service=llm_service,
    tex_service=tex_service,
)


# Helper to run async functions in Streamlit
def run_async(func):
    """Run an async function from Streamlit."""
    return asyncio.run(func)


# App state
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "resume_id" not in st.session_state:
    st.session_state.resume_id = None
if "resume_content" not in st.session_state:
    st.session_state.resume_content = None
if "cover_letter" not in st.session_state:
    st.session_state.cover_letter = None
if "resume_latex" not in st.session_state:
    st.session_state.resume_latex = None
if "cover_letter_latex" not in st.session_state:
    st.session_state.cover_letter_latex = None

# App title
st.title("Resume Builder")

# Sidebar with login
with st.sidebar:
    st.header("User Settings")
    user_input = st.text_input("Enter User ID", value=st.session_state.user_id or "")

    if st.button("Set User"):
        st.session_state.user_id = user_input
        st.success(f"User ID set to: {user_input}")

# Main content
if not st.session_state.user_id:
    st.info("Please enter a User ID in the sidebar to get started.")
else:
    # Initialize services for the user
    async def init_services():
        await prompt_service.set_user_id(st.session_state.user_id)
        await llm_service.configure_for_user(st.session_state.user_id)
        await resume_service.configure_for_user(st.session_state.user_id)

    if st.button("Initialize Services"):
        with st.spinner("Initializing services..."):
            run_async(init_services())
            st.success("Services initialized for user")

    # Resume selection tab
    st.header("Resume Selection")

    async def load_user_resumes():
        return await resume_repository.get_by_user_id(st.session_state.user_id)

    if st.button("Load Resumes"):
        with st.spinner("Loading resumes..."):
            resumes = run_async(load_user_resumes())
            if resumes:
                resume_options = {f"{r.title} ({r.id})": str(r.id) for r in resumes}
                selected_resume = st.selectbox(
                    "Select a resume",
                    options=list(resume_options.keys()),
                    key="resume_select",
                )
                if selected_resume:
                    st.session_state.resume_id = resume_options[selected_resume]
                    st.success(f"Selected resume: {selected_resume}")
            else:
                st.warning("No resumes found for this user")

    # Resume generation tab
    if st.session_state.resume_id:
        st.header("Resume Generation")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Generate Resume Content")
            if st.button("Generate Resume"):
                with st.spinner("Generating resume content..."):

                    async def gen_resume():
                        return await resume_service.generate_resume_content(
                            st.session_state.resume_id
                        )

                    st.session_state.resume_content = run_async(gen_resume())
                    st.success("Resume content generated!")

        with col2:
            st.subheader("Generate Cover Letter")
            if st.button("Generate Cover Letter") and st.session_state.resume_content:
                with st.spinner("Generating cover letter..."):

                    async def gen_cover_letter():
                        return await resume_service.generate_cover_letter(
                            st.session_state.resume_id, st.session_state.resume_content
                        )

                    st.session_state.cover_letter = run_async(gen_cover_letter())
                    st.success("Cover letter generated!")

        # Display generated content
        st.header("Generated Content")

        tab1, tab2 = st.tabs(["Resume Content", "Cover Letter"])

        with tab1:
            if st.session_state.resume_content:
                for section, content in st.session_state.resume_content.items():
                    st.subheader(section.replace("_", " ").title())
                    st.write(content)

                if st.button("Generate Resume LaTeX"):
                    with st.spinner("Generating LaTeX..."):

                        async def gen_latex():
                            return await resume_service.generate_latex(
                                st.session_state.resume_id,
                                st.session_state.resume_content,
                                is_cover_letter=False,
                            )

                        st.session_state.resume_latex = run_async(gen_latex())
                        st.success("Resume LaTeX generated!")

                if st.session_state.resume_latex:
                    st.subheader("LaTeX Output")
                    st.text_area(
                        "Resume LaTeX", st.session_state.resume_latex, height=300
                    )

                    if st.button("Save Resume LaTeX"):
                        output_path = Path("my_data/output")
                        output_path.mkdir(parents=True, exist_ok=True)
                        with open(output_path / "resume.tex", "w") as f:
                            f.write(st.session_state.resume_latex)
                        st.success(
                            f"Resume LaTeX saved to {output_path / 'resume.tex'}"
                        )

        with tab2:
            if st.session_state.cover_letter:
                st.write(st.session_state.cover_letter)

                if st.button("Generate Cover Letter LaTeX"):
                    with st.spinner("Generating LaTeX..."):

                        async def gen_latex():
                            return await resume_service.generate_latex(
                                st.session_state.resume_id,
                                st.session_state.cover_letter,
                                is_cover_letter=True,
                            )

                        st.session_state.cover_letter_latex = run_async(gen_latex())
                        st.success("Cover letter LaTeX generated!")

                if st.session_state.cover_letter_latex:
                    st.subheader("LaTeX Output")
                    st.text_area(
                        "Cover Letter LaTeX",
                        st.session_state.cover_letter_latex,
                        height=300,
                    )

                    if st.button("Save Cover Letter LaTeX"):
                        output_path = Path("my_data/output")
                        output_path.mkdir(parents=True, exist_ok=True)
                        with open(output_path / "cover_letter.tex", "w") as f:
                            f.write(st.session_state.cover_letter_latex)
                        st.success(
                            f"Cover letter LaTeX saved to {output_path / 'cover_letter.tex'}"
                        )

# Run the app with: streamlit run scripts/examples/streamlit_ui.py
