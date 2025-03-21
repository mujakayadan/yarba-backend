"""Database viewer component."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd
import streamlit as st
from streamlit_pdf_viewer import pdf_viewer

from config.logging_config import get_logger
from config.settings import Settings
from core.database.factory import get_unit_of_work
from core.models.resume import Resume

logger = get_logger(__name__)
settings = Settings()


class DatabaseViewer:
    """Component for viewing and managing saved resumes and documents."""

    def __init__(self):
        """Initialize the database viewer."""
        pass

    def get_display_name(self, resume: Resume) -> str:
        """Generate a display name for the resume.

        Args:
            resume: Resume object

        Returns:
            str: Display name for the resume
        """
        # Find a suitable name
        if resume.job_position:
            name = f"{resume.job_position}"
        elif resume.company_details:
            name = f"Resume for {resume.company_details}"
        else:
            name = f"Resume {resume.id}"

        # Add date
        if resume.created_at:
            date_str = resume.created_at.strftime("%Y-%m-%d")
            return f"{name} ({date_str})"

        return name

    def fetch_resumes(self):
        """Fetch resumes for the current user"""

        async def _fetch():
            try:
                # Get resumes from database
                async for uow in get_unit_of_work():
                    resumes = await uow.resume_repository.get_by_user_id(
                        st.session_state["user_id"]
                    )

                    # Convert to simplified format for display
                    resume_data = []
                    for resume in resumes:
                        resume_dict = {
                            "id": str(resume.id),
                            "title": resume.title,
                            "company": resume.company_details,
                            "position": resume.job_position,
                            "created_at": (
                                resume.created_at.strftime("%Y-%m-%d %H:%M")
                                if resume.created_at
                                else "Unknown"
                            ),
                        }
                        resume_data.append(resume_dict)

                    return resume_data
            except Exception as e:
                self.logger.error(f"Error fetching resumes: {e}")
                return []

    def render(self):
        """Render the database viewer component."""
        st.title("📊 Resume Database")

        try:
            # Run the async fetch operation
            if "loop" not in st.session_state:
                st.error("Event loop not available. Please restart the application.")
                return

            resumes = st.session_state.loop.run_until_complete(self.fetch_resumes())

            if not resumes:
                st.info("No resumes found. Create your first resume to get started!")
                return

            # Calculate statistics
            total_resumes = len(resumes)
            resumes_with_pdf = sum(1 for r in resumes if r.resume_pdf_path)
            cover_letters = sum(1 for r in resumes if r.cover_letter_pdf_path)

            # Display statistics in columns
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Total Resumes", total_resumes, help="Total number of resumes"
                )

            with col2:
                st.metric(
                    "Resumes with PDF",
                    resumes_with_pdf,
                    help="Completed resumes with PDF",
                )

            with col3:
                st.metric("Cover Letters", cover_letters, help="Cover letters with PDF")

            # Add a separator
            st.divider()

            # Convert resumes to DataFrame format
            df_data = [
                {
                    "ID": str(resume.id),
                    "Display Name": self.get_display_name(resume),
                    "Company": resume.company_details or "N/A",
                    "Position": resume.job_position or "N/A",
                    "Has Resume": "✅" if resume.resume_pdf_path else "❌",
                    "Has Cover Letter": "✅" if resume.cover_letter_pdf_path else "❌",
                    "Created At": (
                        resume.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        if resume.created_at
                        else "Unknown"
                    ),
                    "Updated At": (
                        resume.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                        if resume.updated_at
                        else "Unknown"
                    ),
                }
                for resume in resumes
            ]
            df = pd.DataFrame(df_data)

            # Sort by creation date in descending order
            if not df.empty and "Created At" in df.columns:
                df = df.sort_values("Created At", ascending=False)

            # Display the DataFrame
            st.dataframe(
                df[
                    [
                        "Display Name",
                        "Company",
                        "Position",
                        "Has Resume",
                        "Has Cover Letter",
                        "Created At",
                    ]
                ],
                use_container_width=True,
            )

            if not df.empty:
                # Allow user to select a resume by display name
                selected_display_name = st.selectbox(
                    "Select a resume to view details:",
                    df["Display Name"].tolist(),
                    index=0,
                )

                # Get the corresponding resume ID and fetch the full resume
                selected_id = df[df["Display Name"] == selected_display_name][
                    "ID"
                ].iloc[0]

                async def get_selected_resume():
                    async for uow in get_unit_of_work():
                        return await uow.resume_repository.get_by_id(selected_id)

                selected_resume = st.session_state.loop.run_until_complete(
                    get_selected_resume()
                )

                if selected_resume:
                    # Create tabs for different views
                    tab1, tab2, tab3 = st.tabs(
                        ["📝 Content", "📄 Documents", "🔄 Actions"]
                    )

                    with tab1:
                        st.subheader(f"Details for: {selected_display_name}")

                        # Job details
                        with st.expander("Job Details", expanded=True):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(
                                    f"**Position:** {selected_resume.job_position or 'N/A'}"
                                )
                                st.markdown(
                                    f"**Company:** {selected_resume.company_details or 'N/A'}"
                                )
                            with col2:
                                st.markdown(
                                    f"**Created:** {selected_resume.created_at.strftime('%Y-%m-%d') if selected_resume.created_at else 'N/A'}"
                                )
                                st.markdown(
                                    f"**Updated:** {selected_resume.updated_at.strftime('%Y-%m-%d') if selected_resume.updated_at else 'N/A'}"
                                )

                        # Job description
                        if selected_resume.job_description:
                            with st.expander("Job Description"):
                                st.markdown(selected_resume.job_description)

                        # Resume JSON content
                        if selected_resume.content:
                            with st.expander("Resume Content"):
                                if isinstance(selected_resume.content, dict):
                                    st.json(selected_resume.content)
                                else:
                                    st.markdown(str(selected_resume.content))

                        # Cover letter content
                        if selected_resume.cover_letter_content:
                            with st.expander("Cover Letter Content"):
                                if isinstance(
                                    selected_resume.cover_letter_content, dict
                                ):
                                    st.json(selected_resume.cover_letter_content)
                                else:
                                    st.markdown(
                                        str(selected_resume.cover_letter_content)
                                    )

                    with tab2:
                        col1, col2 = st.columns(2)

                        with col1:
                            st.subheader("Resume")
                            if selected_resume.resume_pdf_path:
                                # Check if the PDF exists
                                pdf_path = Path(selected_resume.resume_pdf_path)
                                if pdf_path.exists():
                                    # Read and display the PDF
                                    with open(pdf_path, "rb") as f:
                                        pdf_bytes = f.read()
                                        st.download_button(
                                            "⬇️ Download Resume PDF",
                                            pdf_bytes,
                                            file_name=f"{selected_display_name.replace(' ', '_')}_resume.pdf",
                                            mime="application/pdf",
                                        )
                                        # Display PDF
                                        pdf_viewer(pdf_bytes)
                                else:
                                    st.warning(f"PDF file not found at: {pdf_path}")
                            else:
                                st.info("No resume PDF available")

                        with col2:
                            st.subheader("Cover Letter")
                            if selected_resume.cover_letter_pdf_path:
                                # Check if the PDF exists
                                pdf_path = Path(selected_resume.cover_letter_pdf_path)
                                if pdf_path.exists():
                                    # Read and display the PDF
                                    with open(pdf_path, "rb") as f:
                                        pdf_bytes = f.read()
                                        st.download_button(
                                            "⬇️ Download Cover Letter PDF",
                                            pdf_bytes,
                                            file_name=f"{selected_display_name.replace(' ', '_')}_cover_letter.pdf",
                                            mime="application/pdf",
                                        )
                                        # Display PDF
                                        pdf_viewer(pdf_bytes)
                                else:
                                    st.warning(f"PDF file not found at: {pdf_path}")
                            else:
                                st.info("No cover letter PDF available")

                    with tab3:
                        st.subheader("Actions")

                        # Regenerate options
                        st.markdown("### Regenerate Documents")
                        regenerate_type = st.radio(
                            "Document type to regenerate:",
                            ["Resume", "Cover Letter", "Both"],
                            horizontal=True,
                        )

                        if st.button(
                            "Regenerate Selected Document", use_container_width=True
                        ):
                            st.session_state["current_resume_id"] = selected_id
                            st.info(
                                f"Set resume ID {selected_id} for regeneration. Go to the Home page to generate."
                            )

                        st.divider()

                        # Delete options
                        st.markdown("### Delete Documents")

                        delete_button = st.button(
                            "🗑️ Delete This Resume",
                            use_container_width=True,
                            type="primary",
                            help="This will permanently delete this resume and all associated documents",
                        )

                        if delete_button:
                            confirm = st.text_input(
                                "Type 'DELETE' to confirm deletion:",
                                key="delete_confirm",
                            )

                            if confirm == "DELETE":
                                # Delete the resume
                                async def delete_resume():
                                    async for uow in get_unit_of_work():
                                        await uow.resume_repository.delete(selected_id)
                                        return True

                                deleted = st.session_state.loop.run_until_complete(
                                    delete_resume()
                                )
                                if deleted:
                                    st.success(
                                        f"Resume '{selected_display_name}' deleted successfully!"
                                    )
                                    st.rerun()

        except Exception as e:
            logger.error(f"Error in database viewer: {e}", exc_info=True)
            st.error(f"An error occurred while loading the resume database: {str(e)}")

    def delete_resume(self, resume_id):
        """Delete a resume by ID"""

        async def _delete():
            try:
                async for uow in get_unit_of_work():
                    # Get the resume
                    resume = await uow.resume_repository.get_by_id(resume_id)

                    if not resume:
                        return False, "Resume not found"

                    # Check ownership
                    if str(resume.user_id) != st.session_state.get("user_id"):
                        return False, "You do not have permission to delete this resume"

                    # Delete the resume
                    await uow.resume_repository.delete(resume_id)
                    return True, "Resume deleted successfully"
            except Exception as e:
                self.logger.error(f"Error deleting resume: {e}")
                return False, f"Error: {str(e)}"

    def view_resume_content(self, resume_id):
        """View resume content"""

        async def _fetch_content():
            try:
                async for uow in get_unit_of_work():
                    # Get the resume
                    resume = await uow.resume_repository.get_by_id(resume_id)

                    if not resume:
                        return None, "Resume not found"

                    # Check ownership
                    if str(resume.user_id) != st.session_state.get("user_id"):
                        return None, "You do not have permission to view this resume"

                    # Get profile data
                    profile = await uow.profile_repository.get_by_id(resume.profile_id)

                    return {"resume": resume, "profile": profile}, "Success"
            except Exception as e:
                self.logger.error(f"Error fetching resume content: {e}")
                return None, f"Error: {str(e)}"
