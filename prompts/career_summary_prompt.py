"""Prompt template for career summary."""

from .base import BasePrompt

TEMPLATE = """Task: Based on the provided job description, candidate's job titles, and years of experience, create a concise career summary for the resume.

Instructions:
- Select the most appropriate job title from the candidate's history that best aligns with the target position
- Use the candidate's actual years of experience (do not inflate or reduce)
- Create a summary between ${career_summary_details_min_words} and ${career_summary_details_max_words} words
- Focus on skills and experiences that directly relate to the job description
- Only reference skills, technologies, and experiences the candidate actually has - do not fabricate or assume
- Use strong action verbs and quantify achievements where possible
- Ensure the summary highlights the candidate's unique value proposition for the role
- Format the default_summary to flow naturally as a continuation of "with X years of experience..."

Output Format:
Your response should be structured as a valid JSON object matching the CareerSummarySchema format.
The structure should be:
```json
{
  "job_titles": ["Primary Job Title", "Alternative Title 1", "Alternative Title 2"],
  "years_of_experience": "X",
  "default_summary": "implementing and managing... (continuing the sentence as a natural flow)"
}
```

Example:
{
  "job_titles": ["Computer Vision Engineer", "Machine Learning Engineer", "AI Developer"],
  "years_of_experience": "3",
  "default_summary": "implementing highly scalable robust industrial computer vision applications using machine learning algorithms. Proficient in algorithm development, research and development processes, and finding suitable solutions for complex industrial needs. Hands-on using Python, Matlab, C++, OpenCV, and Deep Learning libraries."
}

Note: The default_summary should begin with a lowercase word as it continues a sentence that begins with "A [Job Title] with [X] years of experience..."."""


class CareerSummaryPrompt(BasePrompt):
    """Career Summary prompt template."""

    def __init__(self):
        """Initialize the career summary prompt template."""
        super().__init__(TEMPLATE)


CAREER_SUMMARY_PROMPT = CareerSummaryPrompt()
