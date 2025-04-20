"""Prompt template for personal information."""

from .base_prompt import BasePrompt

TEMPLATE = """Extract or generate personal information from the provided context.

Instructions:
- Provide complete and accurate personal information for the user's resume
- Include full name, email, and phone number as required fields
- Add optional fields like address, LinkedIn, GitHub, and personal website if available
- Ensure the email follows a valid format
- Format phone numbers consistently (e.g., 123-456-7890)
- URLs should include the full path with https://

Output Format:
Your response should be structured as a valid JSON object matching the PersonalInformationSchema format.
The structure should be:
```json
{
  "full_name": "Full Name",
  "email": "email@example.com",
  "phone": "123-456-7890",
  "address": "City, State",
  "linkedin": "https://www.linkedin.com/in/username/",
  "github": "https://github.com/username",
  "website": "https://www.personalwebsite.com"
}
```

Example:
{
  "full_name": "Muja Kayadan",
  "email": "mujakayadan@outlook.com",
  "phone": "641-233-9607",
  "address": "San Francisco, CA",
  "linkedin": "https://www.linkedin.com/in/muja-kayadan/",
  "github": "https://github.com/mucahitkayadan",
  "website": "https://www.mujakayadan.com"
}

Note: If selecting an address from multiple options, choose the one closest to the job location mentioned in the job description. If no job location is provided, use the primary address or default to "San Francisco, CA"."""


class PersonalInformationPrompt(BasePrompt):
    """Personal Information prompt template."""

    def __init__(self):
        """Initialize the personal information prompt template."""
        super().__init__(TEMPLATE)


PERSONAL_INFORMATION_PROMPT = PersonalInformationPrompt()
