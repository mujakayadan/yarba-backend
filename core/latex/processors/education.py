"""Education section processor."""

from typing import Any

from ..utils.safety import sanitize_latex
from .base import SectionProcessor


class EducationProcessor(SectionProcessor):
    """Processor for education section."""

    def _extract_degree(self, edu: dict) -> str:
        """Combine degree_type and degree into a full degree string."""
        degree_type = sanitize_latex(edu.get("degree_type", ""))
        degree = sanitize_latex(edu.get("degree", ""))

        if degree_type and degree:
            return f"{degree_type} in {degree}"
        if degree_type:
            return degree_type
        if degree:
            return degree

        field = sanitize_latex(edu.get("field_of_study", ""))
        return field

    def _extract_courses(self, edu: dict) -> str:
        """Extract key_courses or transcript from an education entry."""
        for key in ("key_courses", "transcript"):
            courses = edu.get(key)
            if not courses:
                continue
            if isinstance(courses, list):
                return sanitize_latex(", ".join(courses))
            if isinstance(courses, str):
                return sanitize_latex(courses)
        return ""

    def process(self, content: Any) -> str:
        """Process education data into LaTeX content.

        Args:
            content: Education data

        Returns:
            LaTeX content for education
        """
        # Parse the content
        data = self.parse_content(content)

        # Handle empty case
        if not data:
            return "\\resumeEducationHeading\n{University Name}\n{Location}\n{Degree}\n{Time Period}\n{Key Courses}"

        result = []

        # Process list of education entries
        if isinstance(data, list):
            for edu in data:
                if not isinstance(edu, dict):
                    continue

                # Extract education details with defaults and handle field name variations
                # Try different variations of university field names
                university = ""
                if "university" in edu:
                    university = sanitize_latex(edu.get("university", ""))
                elif "university_name" in edu:
                    university = sanitize_latex(edu.get("university_name", ""))
                elif "school" in edu:
                    university = sanitize_latex(edu.get("school", ""))

                # Extract location with fallbacks
                location = ""
                if "location" in edu:
                    location = sanitize_latex(edu.get("location", ""))

                degree = self._extract_degree(edu)

                # Extract time period with fallbacks
                time = ""
                if "time" in edu:
                    time = sanitize_latex(edu.get("time", ""))
                elif "graduation_date" in edu:
                    time = sanitize_latex(edu.get("graduation_date", ""))

                key_courses = self._extract_courses(edu)

                # Ensure all fields have values (even if empty) to avoid LaTeX errors
                university = university or "University Name"
                location = location or "Location"
                degree = degree or "Degree"
                time = time or "Time Period"

                # Format the education entry using the education_item template format
                education_content = f"\\resumeEducationHeading\n{{{university}}}\n{{{location}}}\n{{{degree}}}\n{{{time}}}\n{{{key_courses}}}"
                result.append(education_content)

        # Handle dictionary format (single education entry or nested)
        elif isinstance(data, dict):
            # Check if it's a dictionary with nested education entries
            if "education" in data and isinstance(data["education"], list):
                for edu in data["education"]:
                    if not isinstance(edu, dict):
                        continue

                    # Extract fields with all variations
                    university = ""
                    if "university" in edu:
                        university = sanitize_latex(edu.get("university", ""))
                    elif "university_name" in edu:
                        university = sanitize_latex(edu.get("university_name", ""))
                    elif "school" in edu:
                        university = sanitize_latex(edu.get("school", ""))

                    location = sanitize_latex(edu.get("location", ""))
                    degree = self._extract_degree(edu)

                    time = ""
                    if "time" in edu:
                        time = sanitize_latex(edu.get("time", ""))
                    elif "graduation_date" in edu:
                        time = sanitize_latex(edu.get("graduation_date", ""))

                    key_courses = self._extract_courses(edu)

                    # Ensure all fields have values (even if empty) to avoid LaTeX errors
                    university = university or "University Name"
                    location = location or "Location"
                    degree = degree or "Degree"
                    time = time or "Time Period"

                    education_content = f"\\resumeEducationHeading\n{{{university}}}\n{{{location}}}\n{{{degree}}}\n{{{time}}}\n{{{key_courses}}}"
                    result.append(education_content)
            else:
                # It's a single education entry
                university = ""
                if "university" in data:
                    university = sanitize_latex(data.get("university", ""))
                elif "university_name" in data:
                    university = sanitize_latex(data.get("university_name", ""))
                elif "school" in data:
                    university = sanitize_latex(data.get("school", ""))

                location = sanitize_latex(data.get("location", ""))
                degree = self._extract_degree(data)

                time = ""
                if "time" in data:
                    time = sanitize_latex(data.get("time", ""))
                elif "graduation_date" in data:
                    time = sanitize_latex(data.get("graduation_date", ""))

                key_courses = self._extract_courses(data)

                # Ensure all fields have values (even if empty) to avoid LaTeX errors
                university = university or "University Name"
                location = location or "Location"
                degree = degree or "Degree"
                time = time or "Time Period"

                education_content = f"\\resumeEducationHeading\n{{{university}}}\n{{{location}}}\n{{{degree}}}\n{{{time}}}\n{{{key_courses}}}"
                result.append(education_content)

        # If no valid entries, return a placeholder to avoid LaTeX errors
        if not result:
            # Add a placeholder education entry to avoid LaTeX errors
            return "\\resumeEducationHeading\n{University Name}\n{Location}\n{Degree}\n{Time Period}\n{Key Courses}"

        # Return the fully formatted education section
        return f"% Education\n\\section{{Education}}\n\\vspace{{3pt}}\n\\resumeSubHeadingListStart\n{'\n'.join(result)}\n\\resumeSubHeadingListEnd\n\n"
