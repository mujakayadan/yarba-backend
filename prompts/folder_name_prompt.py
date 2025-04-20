"""Prompt template for folder name."""

from .base_prompt import BasePrompt

TEMPLATE = """Task: Extract the company name and job title from the given job description.

Instructions:
- CLOSELY ANALYZE the job description to identify the company name and job title
- Extract the EXACT company name as it appears in the description
- Extract the EXACT job title as it appears in the description
- DO NOT return empty values - if a field cannot be determined with certainty, use "unknown_company" or "unknown_position"
- Use lowercase with underscores instead of spaces for both fields
- Use only alphanumeric characters, underscores, and hyphens
- Make sure the output uses only characters that would be valid in a file path
- Remove any special characters that would cause problems in file systems

IMPORTANT:
- If the company name is not explicitly stated, look for clues like "About Us", "Our Company", "We are", etc.
- If the job title is not in the heading, look at the role description and responsibilities

Output Format:
Your response must be a valid JSON object with EXACTLY this structure:
```json
{
  "company_name": "extracted_company_name",
  "job_title": "extracted_job_title"
}
```

Example:
{
  "company_name": "meta",
  "job_title": "machine_learning_engineer"
}

DO NOT include any other text, explanations, or comments in your response - ONLY the JSON object."""


class FolderNamePrompt(BasePrompt):
    """Folder Name prompt template."""

    def __init__(self):
        """Initialize the folder name prompt template."""
        super().__init__(TEMPLATE)


FOLDER_NAME_PROMPT = FolderNamePrompt()
