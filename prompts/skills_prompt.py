"""Prompt template for skills."""

from .base import BasePrompt

TEMPLATE = """Task: Create a structured skills section based on the candidate's skills and the job description.

Instructions:
- Pick only skills provided in the candidate's data - do not add or infer additional skills
- Organize skills into logical categories relevant to the job description
- Prioritize skills that are most relevant to the target position
- Omit any categories or skills not relevant to the job requirements
- Include ${skills_details_max_categories} skill categories maximum
- Include at least ${skills_details_min_skills_per_category} and maximum ${skills_details_max_skills_per_category} skills per category
- Sort skills within each category by relevance to the job

Output Format:
Your response should be structured as a valid JSON object matching the SkillsListSchema format.
The structure should be:
```json
{
  "skills": [
    {
      "category": "Category Name",
      "skills": [
        "Skill 1",
        "Skill 2",
        "Skill 3"
      ]
    },
    ...more skill categories...
  ]
}
```

Example:
{
  "skills": [
    {
      "category": "Languages",
      "skills": [
        "Python",
        "C++",
        "MATLAB"
      ]
    },
    {
      "category": "Computer Vision",
      "skills": [
        "Object Detection",
        "Feature Extraction",
        "Image Processing",
        "Object Tracking",
        "Semantic Segmentation"
      ]
    },
    {
      "category": "Machine Learning",
      "skills": [
        "Convolutional Networks",
        "Transfer Learning",
        "Generative Networks",
        "NLP",
        "Transformers"
      ]
    },
    {
      "category": "Frameworks",
      "skills": [
        "OpenCV",
        "TensorFlow",
        "PyTorch",
        "Keras",
        "Scikit-Learn"
      ]
    }
  ]
}"""


class SkillsPrompt(BasePrompt):
    """Skills prompt template."""

    def __init__(self):
        """Initialize the skills prompt template."""
        super().__init__(TEMPLATE)


SKILLS_PROMPT = SkillsPrompt()
