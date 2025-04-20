"""Prompt template for projects."""

from .base_prompt import BasePrompt

TEMPLATE = """Based on the provided job description and candidate's project experience, create a concise projects section.

Instructions:
- Include maximum ${project_details_max_projects} projects
- For each project, include ${project_details_bullet_points_per_project} bullet points highlighting key aspects or achievements
- Prioritize projects that demonstrate skills and experiences most relevant to the job description
- Highlight technical skills, frameworks, libraries, and technologies used
- Focus on projects that demonstrate expertise related to the target position
- Include quantifiable achievements and impact where possible
- Format dates consistently (MM/YYYY or just YYYY if month is unknown)

Output Format:
Your response should be structured as a valid JSON object matching the ProjectsListSchema format.
The structure should be:
```json
{
  "projects": [
    {
      "name": "Project Name",
      "bullet_points": [
        "Description of the project and your role",
        "Key achievement or impact of the project"
      ],
      "date": "MM/YYYY or YYYY"
    },
    ...more projects...
  ]
}
```

Example:
{
  "projects": [
    {
      "name": "Raspberry Pi-based Wild Boar Detection System | Raspberry Pi4, YOLO5, OpenCV",
      "bullet_points": [
        "Developed a rapid object detection model based on YOLO5 trained specifically on wild boar images to safeguard crops, achieving 92% detection accuracy",
        "Implemented a responsive system that emits noise, activates flashlights, captures videos, and sends email alerts upon detection"
      ],
      "date": "2023"
    },
    {
      "name": "Fairfield Wildlife Surveillance | YOLOv8, Raspberry Pi4, RoboFlow",
      "bullet_points": [
        "Conceptualized and implemented the project's architecture, achieving a 95% F1 score with the YOLOv8 object detection model",
        "Developed a wildlife surveillance website with features like animal class selection, camera inputs, and configurable confidence thresholds"
      ],
      "date": "06/2022"
    }
  ]
}"""


class ProjectsPrompt(BasePrompt):
    """Projects prompt template."""

    def __init__(self):
        """Initialize the projects prompt template."""
        super().__init__(TEMPLATE)


PROJECTS_PROMPT = ProjectsPrompt()
