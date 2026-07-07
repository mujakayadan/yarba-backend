"""Career summary section processor."""

from typing import Any

from ..utils.safety import sanitize_latex
from .base import SectionProcessor


class CareerSummaryProcessor(SectionProcessor):
    """Processor for career summary section."""

    def process(self, content: Any) -> str:
        """Process career summary data into LaTeX content.

        Args:
            content: Career summary data

        Returns:
            LaTeX content for career summary as a formatted string
        """
        # Parse the content
        data = self.parse_content(content)

        # Handle empty case
        if not data:
            return ""

        # Initialize career summary text
        full_summary = ""

        # Handle string directly (simple summary)
        if isinstance(data, str):
            full_summary = sanitize_latex(data)
        # Handle dictionary format
        elif isinstance(data, dict):
            # Extract components consistently. Assume 'years_of_experience' is provided correctly.
            job_title = "Software Engineer"  # Default fallback
            if "job_title" in data and data.get("job_title"):
                job_title = sanitize_latex(data["job_title"])
            elif "default_job_title" in data and data.get("default_job_title"):
                job_title = sanitize_latex(data["default_job_title"])
            elif (
                "job_titles" in data
                and isinstance(data.get("job_titles"), list)
                and data["job_titles"]
            ):
                job_title = sanitize_latex(data["job_titles"][0])

            # Years should be passed in from portfolio data.
            # Check for existence, type, and handle potential None value.
            years = "some"  # Default fallback
            if "years_of_experience" in data:
                years_raw = data.get("years_of_experience")
                if years_raw is not None:
                    # Check if it's a type we can reasonably convert to string
                    if isinstance(years_raw, str | int | float):
                        years = sanitize_latex(str(years_raw))
                    else:
                        self.logger.warning(
                            f"'years_of_experience' has unexpected type: {type(years_raw)}. Using fallback."
                        )
                else:
                    self.logger.warning(
                        "'years_of_experience' is None in career summary data. Using fallback."
                    )
            else:
                self.logger.warning(
                    "'years_of_experience' not found in career summary data. Using fallback."
                )

            # Summary text should now ONLY be the descriptive part from LLM
            summary_description = "expertise in relevant fields."  # Default fallback
            if "default_summary" in data and data.get("default_summary"):
                summary_description = sanitize_latex(data["default_summary"])
            elif "summary" in data and data.get(
                "summary"
            ):  # Fallback to 'summary' if 'default_summary' missing
                summary_description = sanitize_latex(data["summary"])

            # Always construct the full summary string using the standard format
            # Ensure summary_description doesn't start with connector words like 'in' if not needed
            # (This example assumes the LLM provides text like "in X, Y, and Z")
            full_summary = f"A {job_title} with {years} years of experience {summary_description.strip()}"

        # Return the fully formatted career summary section
        # Ensure the section command is generated correctly without being treated as a comment
        formatted_content = (
            f"% Career Summary\n"
            f"\\section{{Career Summary}}\n"
            f"\\careerSummary{{{full_summary}}}\n\n"
        )
        self.logger.debug(f"Processed Career Summary: {formatted_content}")
        return formatted_content
