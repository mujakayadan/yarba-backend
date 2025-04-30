"""Career summary section processor."""

from typing import Any, Dict

from ..utils.safety import sanitize_latex
from .base import SectionProcessor


class CareerSummaryProcessor(SectionProcessor):
    """Processor for career summary section."""

    def process(self, content: Any) -> str:
        """
        Process career summary data into LaTeX content.

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
            # If default_summary exists, use it directly as it already contains the complete sentence
            if "default_summary" in data and data["default_summary"]:
                full_summary = sanitize_latex(data.get("default_summary", ""))
            # If not, try other fields and format appropriately
            else:
                # Get job title
                job_title = ""
                if "default_job_title" in data and data["default_job_title"]:
                    job_title = sanitize_latex(data["default_job_title"])
                elif (
                    "job_titles" in data
                    and isinstance(data["job_titles"], list)
                    and data["job_titles"]
                ):
                    job_title = sanitize_latex(data["job_titles"][0])
                elif "job_title" in data:
                    job_title = sanitize_latex(data.get("job_title", ""))
                else:
                    job_title = "Software Engineer"  # Default fallback

                # Get years of experience
                years = "3"  # Default fallback
                if "years_of_experience" in data:
                    years = sanitize_latex(str(data.get("years_of_experience", "")))

                # Get summary text from other possible fields
                summary = ""
                if "summary" in data:
                    summary = sanitize_latex(data.get("summary", ""))
                elif "career_summary" in data:
                    summary = sanitize_latex(data.get("career_summary", ""))

                # Format complete summary if we need to build it
                full_summary = (
                    f"A {job_title} with {years} years of experience {summary}"
                )

        # Return the fully formatted career summary section
        formatted_content = f"% Career Summary\n\\section{{Career Summary}}\n\\careerSummary{{{full_summary}}}\n\n"

        self.logger.debug(
            f"Career summary processed: summary_length={len(full_summary)}"
        )

        return formatted_content
