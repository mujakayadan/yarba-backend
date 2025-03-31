"""Work experience section processor."""

from typing import Any, Dict, List

from ..utils.sanitizer import sanitize_latex
from .base import SectionProcessor


class WorkExperienceProcessor(SectionProcessor):
    """Processor for work experience section."""

    def process(self, content: Any) -> str:
        """
        Process work experience into LaTeX content.

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

        # Handle dictionary format with nested work_experience
        if (
            isinstance(data, dict)
            and "work_experience" in data
            and isinstance(data["work_experience"], list)
        ):
            jobs = data["work_experience"]
            for job in jobs:
                if not isinstance(job, dict):
                    continue

                # Extract job details with defaults
                job_title = sanitize_latex(job.get("job_title", ""))
                company = sanitize_latex(job.get("company", ""))
                location = sanitize_latex(job.get("location", ""))
                time = sanitize_latex(job.get("time", ""))
                responsibilities = job.get("responsibilities", [])

                # Process responsibilities
                resp_items = []
                if isinstance(responsibilities, list):
                    for item in responsibilities:
                        resp_items.append(f"\\resumeItem{{{sanitize_latex(item)}}}")
                elif isinstance(responsibilities, str):
                    resp_items.append(
                        f"\\resumeItem{{{sanitize_latex(responsibilities)}}}"
                    )

                # Format the job using the resumeSubheading command
                job_content = f"\\resumeSubheading\n    {{{job_title}}}{{{time}}}\n    {{{company}}}{{{location}}}\n    \\resumeItemListStart\n{chr(10).join(resp_items)}\n    \\resumeItemListEnd"
                result.append(job_content)
        # Process list of work experiences
        elif isinstance(data, list):
            for job in data:
                if not isinstance(job, dict):
                    continue

                # Extract job details with defaults
                job_title = sanitize_latex(job.get("job_title", ""))
                company = sanitize_latex(job.get("company", ""))
                location = sanitize_latex(job.get("location", ""))
                time = sanitize_latex(job.get("time", ""))
                responsibilities = job.get("responsibilities", [])

                # Process responsibilities
                resp_items = []
                if isinstance(responsibilities, list):
                    for item in responsibilities:
                        resp_items.append(f"\\resumeItem{{{sanitize_latex(item)}}}")
                elif isinstance(responsibilities, str):
                    resp_items.append(
                        f"\\resumeItem{{{sanitize_latex(responsibilities)}}}"
                    )

                # Format the job using the resumeSubheading command
                job_content = f"\\resumeSubheading\n    {{{job_title}}}{{{time}}}\n    {{{company}}}{{{location}}}\n    \\resumeItemListStart\n{chr(10).join(resp_items)}\n    \\resumeItemListEnd"
                result.append(job_content)

        # Handle dictionary format (single job)
        elif isinstance(data, dict):
            job_title = sanitize_latex(data.get("job_title", ""))
            company = sanitize_latex(data.get("company", ""))
            location = sanitize_latex(data.get("location", ""))
            time = sanitize_latex(data.get("time", ""))
            responsibilities = data.get("responsibilities", [])

            # Process responsibilities
            resp_items = []
            if isinstance(responsibilities, list):
                for item in responsibilities:
                    resp_items.append(f"\\resumeItem{{{sanitize_latex(item)}}}")
            elif isinstance(responsibilities, str):
                resp_items.append(f"\\resumeItem{{{sanitize_latex(responsibilities)}}}")

            # Format the job
            job_content = f"\\resumeSubheading\n    {{{job_title}}}{{{time}}}\n    {{{company}}}{{{location}}}\n    \\resumeItemListStart\n{chr(10).join(resp_items)}\n    \\resumeItemListEnd"
            result.append(job_content)

        return "\n".join(result)
