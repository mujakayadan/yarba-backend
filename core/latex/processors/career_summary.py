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
            LaTeX content for career summary
        """
        # Parse the content
        data = self.parse_content(content)

        # Handle empty case
        if not data:
            return ""

        # Handle string directly (simple summary)
        if isinstance(data, str):
            # Format for careerSummary with default job title and years
            return (
                f"\\careerSummary{{Software Engineer}}{{3}}{{{sanitize_latex(data)}}}"
            )

        # Handle dictionary format
        if isinstance(data, dict):
            # Extract career summary details with defaults
            # Try various field names that might contain job title
            job_title = "Software Engineer"
            if "job_title" in data:
                job_title = sanitize_latex(data.get("job_title", ""))
            elif (
                "job_titles" in data
                and isinstance(data["job_titles"], list)
                and data["job_titles"]
            ):
                job_title = sanitize_latex(data["job_titles"][0])

            # Try various field names for years of experience
            years = "3"
            if "years_of_experience" in data:
                years = sanitize_latex(data.get("years_of_experience", ""))

            # Try various field names for the summary text
            summary = ""
            if "summary" in data:
                summary = sanitize_latex(data.get("summary", ""))
            elif "career_summary" in data:
                summary = sanitize_latex(data.get("career_summary", ""))
            elif "default_summary" in data:
                summary = sanitize_latex(data.get("default_summary", ""))

            # Format for careerSummary command
            return f"\\careerSummary{{{job_title}}}{{{years}}}{{{summary}}}"

        # If none of the above, return empty string
        return ""
