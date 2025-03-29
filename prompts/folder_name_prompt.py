"""Prompt template for folder name."""

from .base import BasePrompt

TEMPLATE = """Task: Extract the company name and job title from the given job description.

Instructions:
- Extract the company name and position title from the job description
- Both should be in lowercase with underscores instead of spaces
- Use only alphanumeric characters, underscores, and hyphens
- If the company name or job title cannot be determined, use "unknown"
- Make sure the output uses only characters that would be valid in a file path
- Remove any special characters that would cause problems in file systems

Output Format:
Your response should be structured as a valid JSON object matching the CompanyJobSchema format.
The structure should be:
```json
{
  "company_name": "company_name",
  "job_title": "job_title"
}
```

Example:
{
  "company_name": "meta",
  "job_title": "machine_learning_engineer"
}"""


class FolderNamePrompt(BasePrompt):
    """Folder Name prompt template."""

    def __init__(self):
        """Initialize the folder name prompt template."""
        super().__init__(TEMPLATE)


FOLDER_NAME_PROMPT = FolderNamePrompt()
