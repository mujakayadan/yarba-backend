"""Prompt template for work experience."""

from .base import BasePrompt

TEMPLATE = """Based on the provided job description and candidate's work experience, create a concise work experience section.

Important instructions:
1. List jobs in reverse chronological order (most recent first)
2. Include ${work_experience_details_max_jobs} jobs
3. Each job should have exactly ${work_experience_details_bullet_points_per_job} bullet points
4. Focus on relevant experiences and accomplishments that demonstrate skills applicable to the target position
5. Use action verbs and quantifiable achievements wherever possible
6. Ensure each bullet point is concise and highlights a specific achievement or responsibility
7. Format dates consistently (MM/YYYY - MM/YYYY or "Present" for current positions)

Output Format:
Your response should be structured as a valid JSON object matching the WorkExperienceListSchema format.
The structure should be:
```json
{
  "work_experience": [
    {
      "job_title": "Job Title",
      "company": "Company Name",
      "location": "City, Country",
      "time": "MM/YYYY - MM/YYYY",
      "responsibilities": [
        "Accomplishment or responsibility 1",
        "Accomplishment or responsibility 2"
      ]
    },
    ...more jobs...
  ]
}
```

Example:
{
  "work_experience": [
    {
      "job_title": "R&D Machine Learning Engineer",
      "company": "Orsan (Mercedes-Benz Turk A.S)",
      "location": "Aksaray, Turkiye",
      "time": "06/2020 - 05/2021",
      "responsibilities": [
        "Developed a computer vision solution for laser steel welding quality control using OpenCV and TensorFlow, achieving a 92% accuracy in defect detection and a 30% reduction in welding defects",
        "Engineered a real-time monitoring framework with U-Net-based algorithms, reducing false positives by 25% and optimizing the efficiency of the quality control system"
      ]
    },
    {
      "job_title": "Application Engineer",
      "company": "TeknoWorld GmbH",
      "location": "Dusseldorf, Germany",
      "time": "06/2019 - 10/2019",
      "responsibilities": [
        "Designed and deployed smart camera solutions leveraging Dahua systems for enhanced video analytics, resulting in increased customer satisfaction across over 20 clients",
        "Implemented customized solutions for specific customer needs, demonstrating strong problem-solving skills and adaptability in diverse environments"
      ]
    }
  ]
}"""


class WorkExperiencePrompt(BasePrompt):
    """Work Experience prompt template."""

    def __init__(self):
        """Initialize the work experience prompt template."""
        super().__init__(TEMPLATE)


WORK_EXPERIENCE_PROMPT = WorkExperiencePrompt()
