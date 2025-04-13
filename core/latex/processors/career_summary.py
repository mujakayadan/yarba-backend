"""Career summary section processor."""

from typing import Any, Dict

from ..utils.sanitizer import sanitize_latex
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

        # Initialize default values
        job_title = "Software Engineer"
        years = "3"
        summary = ""

        # Handle string directly (simple summary)
        if isinstance(data, str):
            summary = sanitize_latex(data)
        # Handle dictionary format
        elif isinstance(data, dict):
            # First check for the default_job_title field
            if "default_job_title" in data and data["default_job_title"]:
                job_title = sanitize_latex(data["default_job_title"])
            # Fall back to first job title in the list if default not set
            elif (
                "job_titles" in data
                and isinstance(data["job_titles"], list)
                and data["job_titles"]
            ):
                job_title = sanitize_latex(data["job_titles"][0])
            # Check for a single job_title field
            elif "job_title" in data:
                job_title = sanitize_latex(data.get("job_title", ""))

            # Extract years of experience
            if "years_of_experience" in data:
                years = sanitize_latex(str(data.get("years_of_experience", "")))

            # Extract summary text - prioritize default_summary for portfolio data
            if "default_summary" in data:
                summary = sanitize_latex(data.get("default_summary", ""))
            elif "summary" in data:
                summary = sanitize_latex(data.get("summary", ""))
            elif "career_summary" in data:
                summary = sanitize_latex(data.get("career_summary", ""))

        # Return the fully formatted career summary section
        formatted_content = f"% Career Summary\n\\section{{Career Summary}}\n\\careerSummary{{{job_title}}}{{{years}}}{{{summary}}}\n\n"

        self.logger.debug(
            f"Career summary processed: job_title={job_title}, years={years}, summary_length={len(summary)}"
        )

        return formatted_content
