"""Prompt template for awards."""

from .base import BasePrompt

TEMPLATE = """Task: Based on the provided job description and candidate's achievements, create a concise awards section.

Instructions:
- Include maximum ${awards_details_max_awards} awards or recognitions
- Prioritize awards that are:
  1. Most relevant to the target position and industry
  2. Most recent and significant
  3. Demonstrate technical excellence, leadership, or innovation
- For each award, provide:
  1. Award title/name
  2. Issuing organization, date, and significance (combined in the explanation field)
- Format dates consistently (MM/YYYY)
- Ensure award descriptions highlight the relevance to the target position

Output Format:
Your response should be structured as a valid JSON object matching the AwardsListSchema format.
The structure should be:
```json
{
  "awards": [
    {
      "name": "Award Name",
      "explanation": "Issued by Organization, Date. Brief explanation of significance"
    },
    ...more awards...
  ]
}
```

Example:
{
  "awards": [
    {
      "name": "68th Iowa Reserve Chess Championship Winner",
      "explanation": "Issued by Iowa State Chess Association, 08/2023. 4 Rounds G/60 d5, won with a perfect score of 4/4"
    },
    {
      "name": "High Honors Degree",
      "explanation": "Awarded by Aksaray University, 06/2019. Graduated with a 3.60 GPA as 3rd of the faculty"
    }
  ]
}"""


class AwardsPrompt(BasePrompt):
    """Awards prompt template."""

    def __init__(self):
        """Initialize the awards prompt template."""
        super().__init__(TEMPLATE)


AWARDS_PROMPT = AwardsPrompt()
