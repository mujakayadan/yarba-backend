"""Section selector component."""

from typing import Dict, List, Tuple

import streamlit as st

from config.logging_config import get_logger

logger = get_logger(__name__)


class SectionSelector:
    """Component for selecting and ordering resume sections."""

    def __init__(
        self,
        available_sections: List[str] = None,
        current_order: List[str] = None,
        current_visible: List[str] = None,
    ):
        """
        Initialize the section selector with available sections and current selections.

        Args:
            available_sections: List of available section names
            current_order: Current order of sections
            current_visible: Currently visible sections
        """
        logger.debug("Initializing SectionSelector")

        # Default sections if not provided
        if not available_sections:
            self.available_sections = [
                "personal_information",
                "career_summary",
                "work_experience",
                "education",
                "skills",
                "projects",
                "awards",
                "publications",
            ]
        else:
            self.available_sections = available_sections

        # Default order if not provided
        if not current_order:
            self.current_order = self.available_sections.copy()
        else:
            self.current_order = current_order

        # Default visible sections if not provided
        if not current_visible:
            self.current_visible = self.available_sections[
                :6
            ]  # First 6 sections by default
        else:
            self.current_visible = current_visible

        # Ensure all sections in current_order and current_visible are valid
        self.current_order = [
            s for s in self.current_order if s in self.available_sections
        ]
        self.current_visible = [
            s for s in self.current_visible if s in self.available_sections
        ]

        # Add any missing sections to current_order
        for section in self.available_sections:
            if section not in self.current_order:
                self.current_order.append(section)

    def render(self) -> Tuple[List[str], List[str]]:
        """
        Render the section selector component.

        Returns:
            Tuple[List[str], List[str]]: Tuple of (ordered sections, visible sections)
        """
        st.subheader("Resume Sections")
        st.write(
            "Select which sections to include in your resume and use the arrows to reorder them."
        )

        # Create a list of section names with proper formatting for display
        section_display_names = {
            section: section.replace("_", " ").title()
            for section in self.available_sections
        }

        # Create a list of sections in the current order with checkboxes
        visible_sections = []

        # Use a container for the section list
        for i, section in enumerate(self.current_order):
            # Create a row for each section
            row = st.container()

            # Use columns for the checkbox, name, and buttons
            with row:
                col1, col2, col3, col4 = st.columns([1, 5, 1, 1])

                # Checkbox for visibility
                is_visible = section in self.current_visible
                is_checked = col1.checkbox(
                    f"Include {section}",
                    value=is_visible,
                    key=f"visible_{section}",
                    label_visibility="collapsed",
                )

                # Section name
                col2.write(section_display_names[section])

                # Up button (disabled for first item)
                if i > 0:
                    if col3.button("↑", key=f"up_{section}"):
                        # Swap with previous item
                        self.current_order[i], self.current_order[i - 1] = (
                            self.current_order[i - 1],
                            self.current_order[i],
                        )
                        st.rerun()

                # Down button (disabled for last item)
                if i < len(self.current_order) - 1:
                    if col4.button("↓", key=f"down_{section}"):
                        # Swap with next item
                        self.current_order[i], self.current_order[i + 1] = (
                            self.current_order[i + 1],
                            self.current_order[i],
                        )
                        st.rerun()

                # Add to visible sections if checked
                if is_checked:
                    visible_sections.append(section)

            # Add a separator
            st.divider()

        return self.current_order, visible_sections
