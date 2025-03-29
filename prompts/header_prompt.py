"""Prompt template for header."""

from .base import BasePrompt

TEMPLATE = """Task: Create a structured header section for a resume based on the provided personal information.

Instructions:
- Use ONLY the information provided in the personal information data
- Include all available contact information in a structured format
- Ensure email addresses and phone numbers are formatted consistently
- Format URLs with full paths including https://
- Do not add, invent, or assume any details not explicitly given
- If any standard information is missing, simply omit it from the output

Output Format:
Your response should be structured as a valid JSON object matching the HeaderSchema format.
The structure should be:
```json
{
  "full_name": "Full Name",
  "contact": {
    "email": "email@example.com",
    "phone": "123-456-7890",
    "address": "City, State"
  },
  "profiles": {
    "linkedin": "https://www.linkedin.com/in/username/",
    "github": "https://github.com/username",
    "website": "https://www.personalwebsite.com"
  }
}
```

Example:
{
  "full_name": "John Smith",
  "contact": {
    "email": "john.smith@example.com",
    "phone": "555-123-4567",
    "address": "San Francisco, CA"
  },
  "profiles": {
    "linkedin": "https://www.linkedin.com/in/johnsmith/",
    "github": "https://github.com/johnsmith",
    "website": "https://www.johnsmith.dev"
  }
}"""


class HeaderPrompt(BasePrompt):
    """Header prompt template."""

    def __init__(self):
        """Initialize the header prompt template."""
        super().__init__(TEMPLATE)


HEADER_PROMPT = HeaderPrompt()
