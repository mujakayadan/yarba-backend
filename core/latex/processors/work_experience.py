"""Work experience section processor."""

from typing import Any

from ..utils.safety import sanitize_latex
from .base import SectionProcessor


class WorkExperienceProcessor(SectionProcessor):
    """Processor for work experience section."""

    def process(self, content: Any) -> str:
        """Process work experience into LaTeX content.

        Args:
            content: Work experience data

        Returns:
            LaTeX content for work experience
        """
        # Parse the content
        data = self.parse_content(content)

        # Handle empty case
        if not data:
            return ""

        result = []

        # Define templates directly in the processor
        work_experience_item_template = "\\resumeSubheading\n    {{{job_title}}}{{{time}}}\n    {{{company}}}{{{location}}}\n    \\resumeItemListStart\n{responsibilities}\n    \\resumeItemListEnd\n"
        bullet_point_template = "\\resumeItem{{{content}}}\n"

        # Handle different data structures and standardize to list of entries
        entries = []
        if isinstance(data, dict):
            if "work_experience" in data and isinstance(data["work_experience"], list):
                # Format: {"work_experience": [entry1, entry2, ...]}
                entries = data["work_experience"]
            else:
                # Format: single job entry as dict
                entries = [data]
        elif isinstance(data, list):
            # Format: [entry1, entry2, ...]
            entries = data

        # Process each work experience entry
        for entry in entries:
            if not isinstance(entry, dict):
                continue

            # Extract fields with defaults
            job_title = sanitize_latex(entry.get("job_title", ""))
            company = sanitize_latex(entry.get("company", ""))
            location = sanitize_latex(entry.get("location", ""))
            time = sanitize_latex(entry.get("time", ""))

            # Get responsibilities
            responsibilities = entry.get("responsibilities", [])
            responsibilities_latex = []

            # Handle different formats of responsibilities
            if isinstance(responsibilities, list):
                for resp in responsibilities:
                    responsibilities_latex.append(
                        bullet_point_template.format(content=sanitize_latex(resp))
                    )
            elif isinstance(responsibilities, str):
                # If it's a string, split by newlines
                for line in responsibilities.split("\n"):
                    if line.strip():
                        responsibilities_latex.append(
                            bullet_point_template.format(
                                content=sanitize_latex(line.strip())
                            )
                        )

            # Format the work experience item
            formatted_entry = work_experience_item_template.format(
                job_title=job_title,
                company=company,
                location=location,
                time=time,
                responsibilities="\n".join(responsibilities_latex),
            )

            result.append(formatted_entry)

        # Return the full section with proper formatting
        return f"% Work Experience\n\\section{{Work Experience}}\n\\vspace{{3pt}}\n\\resumeSubHeadingListStart\n{'\n'.join(result)}\n\\resumeSubHeadingListEnd\n\n"
