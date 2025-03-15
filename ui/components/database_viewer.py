"""Database viewer component."""

from datetime import datetime
import asyncio
from typing import List, Optional

import pandas as pd
import streamlit as st
from streamlit_pdf_viewer import pdf_viewer

from config.logging_config import get_logger
from config.settings import Settings
from core.models.resume import Resume
from core.database import get_resume_repository
from core.repositories.resume import ResumeRepository

logger = get_logger(__name__)
settings = Settings()


@st.cache_resource
def get_repository() -> ResumeRepository:
    """Get a cached instance of the resume repository."""
    return ResumeRepository()


class DatabaseViewer:
    def __init__(self):
        self.repository = get_repository()

    def get_display_name(self, resume) -> str:
        """Generate a display name for the resume"""
        if isinstance(resume.personal_information, dict):
            # For structured data
            name = resume.personal_information.get("name", "Unnamed")
        else:
            # For LaTeX format
            name = resume.title or "Unnamed"

        return f"{name}_{resume.created_at.strftime('%Y%m%d')}"

    async def fetch_resumes(self) -> List[Resume]:
        """Fetch resumes for the current user."""
        try:
            # Get resumes for the current user
            resumes = await self.repository.get_by_user_id(st.session_state["user_id"])
            return resumes
        except Exception as e:
            logger.error(f"Error fetching resumes: {e}")
            return []

    def render(self):
        st.title("📊 Resume Database")

        try:
            # Use asyncio to run the async fetch operation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            resumes = loop.run_until_complete(self.fetch_resumes())
            loop.close()

            if not resumes:
                st.info("No resumes found. Create your first resume to get started!")
                return

            # Calculate statistics
            total_resumes = len(resumes)
            today = datetime.now().date()
            today_resumes = sum(1 for r in resumes if r.created_at.date() == today)
            last_7_days = sum(
                1 for r in resumes if (today - r.created_at.date()).days <= 7
            )

            # Display statistics in columns
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Total Resumes", total_resumes, help="Total number of resumes"
                )

            with col2:
                st.metric(
                    "Today's Resumes", today_resumes, help="Resumes created today"
                )

            with col3:
                st.metric("Last 7 Days", last_7_days, help="Resumes in the last week")

            # Add a separator
            st.divider()

            # Convert resumes to DataFrame format
            df_data = [
                {
                    "ID": str(resume.id),
                    "Display Name": self.get_display_name(resume),
                    "Title": resume.title,
                    "Version": resume.version,
                    "Created At": resume.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                }
                for resume in resumes
            ]
            df = pd.DataFrame(df_data)

            # Sort by creation date in descending order
            df = df.sort_values("Created At", ascending=False)

            # Display the DataFrame
            st.dataframe(
                df[["Display Name", "Title", "Version", "Created At"]],
                use_container_width=True,
            )

            if not df.empty:
                # Allow user to select a resume by display name
                selected_display_name = st.selectbox(
                    "Select a resume to view details:",
                    df["Display Name"].tolist(),
                    index=0,
                )

                # Get the corresponding resume
                selected_resume = next(
                    (
                        r
                        for r in resumes
                        if str(r.id)
                        == df[df["Display Name"] == selected_display_name]["ID"].iloc[0]
                    ),
                    None,
                )

                if selected_resume:
                    # Create tabs for different views
                    tab1, tab2 = st.tabs(["📝 Content", "📄 Documents"])

                    with tab1:
                        st.subheader(f"Details for: {selected_display_name}")

                        # Display resume sections in expanders
                        sections = [
                            (
                                "Personal Information",
                                selected_resume.personal_information,
                            ),
                            ("Career Summary", selected_resume.career_summary),
                            ("Skills", selected_resume.skills),
                            ("Work Experience", selected_resume.work_experience),
                            ("Education", selected_resume.education),
                            ("Projects", selected_resume.projects),
                            ("Awards", selected_resume.awards),
                            ("Publications", selected_resume.publications),
                        ]

                        for section_name, content in sections:
                            if content:
                                with st.expander(section_name):
                                    if isinstance(content, (dict, list)):
                                        st.json(content)
                                    else:
                                        st.markdown(content)

                    with tab2:
                        if selected_resume.resume_pdf:
                            st.subheader("Resume PDF")
                            st.download_button(
                                "⬇️ Download Resume PDF",
                                selected_resume.resume_pdf,
                                file_name=f"{selected_display_name}_resume.pdf",
                                mime="application/pdf",
                            )
                            # Display PDF
                            pdf_viewer(selected_resume.resume_pdf)

                        if selected_resume.cover_letter_pdf:
                            st.subheader("Cover Letter PDF")
                            st.download_button(
                                "⬇️ Download Cover Letter PDF",
                                selected_resume.cover_letter_pdf,
                                file_name=f"{selected_display_name}_cover_letter.pdf",
                                mime="application/pdf",
                            )
                            # Display PDF
                            pdf_viewer(selected_resume.cover_letter_pdf)

        except Exception as e:
            logger.error(f"Error in database viewer: {e}")
            st.error(
                "An error occurred while loading the resume database. Please try again later."
            )
