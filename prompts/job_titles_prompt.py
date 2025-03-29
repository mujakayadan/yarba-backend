"""Prompt template for job titles."""

from .base import BasePrompt

TEMPLATE = """Task: Based on the provided job description and candidate's skills, select the most appropriate job title.

Instructions:
- Analyze the job description to identify the primary role and its requirements
- Compare these requirements with the candidate's skills and experience
- Select the job title that best matches the position
- Choose a title that accurately reflects the role's responsibilities
- Use industry-standard job titles rather than creative or company-specific titles
- Consider the seniority level mentioned in the job description

Output Format:
Your response should be structured as a valid JSON object matching the JobTitleSchema format.
The structure should be:
```json
{
  "job_title": "Selected Job Title"
}
```

Example:
{
  "job_title": "Machine Learning Engineer"
}"""


class JobTitlesPrompt(BasePrompt):
    """Job Titles prompt template."""

    def __init__(self):
        """Initialize the job titles prompt template."""
        super().__init__(TEMPLATE)


JOB_TITLES_PROMPT = JobTitlesPrompt()
