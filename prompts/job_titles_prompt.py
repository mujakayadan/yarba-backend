"""Prompt template for job titles."""

from .base import BasePrompt

TEMPLATE = """Based on the provided information, choose the most suitable job title in the list for the job description.

Important instructions:
2. Choose the most suitable job title in the list for the job description.
3. Answer only with the job title. No additional text or explanation is needed."""


class JobTitlesPrompt(BasePrompt):
    """Job Titles prompt template."""

    def __init__(self):
        """Initialize the job titles prompt template."""
        super().__init__(TEMPLATE)


JOB_TITLES_PROMPT = JobTitlesPrompt()
