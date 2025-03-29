"""Prompt template for education."""

from .base import BasePrompt

TEMPLATE = """Task:
Based on the provided job description and the given education information, create a structured education section.

Instructions:
- Include a maximum of ${education_details_max_entries} educational entries, prioritizing the most relevant and recent
- List education in reverse chronological order (most recent first)
- Include only the most relevant educational experiences that support the target position
- For each degree, include up to ${education_details_max_courses} key courses that are most relevant to the job description
- Format degree types consistently (e.g., "B.Sc.", "M.S.", "Ph.D.")
- Include GPA if it's above 3.5 or if it's specifically mentioned as important in the job description
- Focus on education details that demonstrate qualifications for the position

Output Format:
Your response should be structured as a valid JSON object matching the EducationListSchema format.
The structure should be:
```json
{
  "education": [
    {
      "degree_type": "M.S.",
      "degree": "Computer Science",
      "university_name": "University Name",
      "time": "Start Year - End Year",
      "location": "City, Country",
      "GPA": "3.8/4.0",
      "transcript": [
        "Course 1: Advanced Machine Learning",
        "Course 2: Distributed Systems"
      ]
    },
    ...more education entries...
  ]
}
```

Example:
{
  "education": [
    {
      "degree_type": "M.Sc",
      "degree": "Computer Science",
      "university_name": "Maharishi International University",
      "time": "05/2023 - 12/2025",
      "location": "Iowa, US",
      "GPA": "3.9/4.0",
      "transcript": [
        "Artificial Intelligence",
        "Algorithms",
        "Modern Programming Practices"
      ]
    },
    {
      "degree_type": "M.Sc",
      "degree": "ICT for Internet and Multimedia",
      "university_name": "University of Padua",
      "time": "08/2021 - 06/2023",
      "location": "Padua, Italy",
      "GPA": "95/110",
      "transcript": [
        "Computer Vision",
        "Machine Learning",
        "Deep Learning",
        "IoT"
      ]
    }
  ]
}"""


class EducationPrompt(BasePrompt):
    """Education prompt template."""

    def __init__(self):
        """Initialize the education prompt template."""
        super().__init__(TEMPLATE)


EDUCATION_PROMPT = EducationPrompt()
