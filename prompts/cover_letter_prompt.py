"""Prompt template for cover letter."""

from .base import BasePrompt

TEMPLATE = """Task: Create a structured cover letter based on the provided resume content and job description.

Instructions:
- Create a cover letter with ${cover_letter_details_paragraphs} paragraphs
- Write at a ${cover_letter_details_target_grade_level}-year-old reading level
- Use casual, simple language with shorter sentences (avoid excessive conjunctions)
- Draw from the candidate's personal journey and how it shaped their skills
- Tailor the content specifically to the job requirements and company values
- Focus on demonstrating relevant qualifications and enthusiasm for the role
- Use the candidate's actual experiences - do not invent or assume details
- Structure the cover letter with a clear introduction, body, and conclusion
- If a life story is provided, integrate it thoughtfully to create a personal connection, showing how the candidate's background has shaped their career path and makes them uniquely qualified for this role

Paragraph Structure:
1. Introduction: State the position, where you found it, and express enthusiasm
2. Qualifications: Highlight relevant skills and experiences with specific examples
3. Company Alignment: Show how your values align with the company's mission
4. Conclusion: Thank the employer and express interest in further discussion

Output Format:
Your response should be structured as a valid JSON object matching the CoverLetterSchema format.
The structure should be:
```json
{
  "paragraphs": [
    "Introduction paragraph text...",
    "Qualifications paragraph text...",
    "Company alignment paragraph text...",
    "Conclusion paragraph text..."
  ],
  "greeting": "Dear Hiring Manager,",
  "closing": "Sincerely,",
  "full_document": "Full formatted cover letter with all paragraphs, greeting and closing"
}
```

Example:
{
  "paragraphs": [
    "I am excited to apply for the Machine Learning Engineer position at TechCorp that I found on LinkedIn. As someone passionate about developing AI solutions that solve real-world problems, I'm thrilled about the opportunity to join your innovative team.",

    "Throughout my career, I've developed strong expertise in computer vision and machine learning, with a focus on industrial applications. At Orsan, I implemented a quality control system using OpenCV and TensorFlow that achieved 92% accuracy and reduced defects by 30%. My experience with real-time monitoring frameworks and U-Net algorithms directly aligns with the requirements mentioned in your job posting.",

    "What attracts me most to TechCorp is your commitment to advancing AI technology while maintaining a strong ethical framework. Your recent work on transparent AI systems particularly resonates with my belief that technology should be both powerful and accountable. I'm eager to contribute to a team that values innovation and responsible development.",

    "Thank you for considering my application. I would welcome the opportunity to discuss how my background in machine learning and computer vision could contribute to TechCorp's ongoing success. I look forward to potentially joining your team and helping to develop the next generation of AI solutions."
  ],
  "greeting": "Dear Hiring Manager,",
  "closing": "Sincerely,",
  "full_document": "Dear Hiring Manager,\n\nI am excited to apply for the Machine Learning Engineer position at TechCorp that I found on LinkedIn. As someone passionate about developing AI solutions that solve real-world problems, I'm thrilled about the opportunity to join your innovative team.\n\nThroughout my career, I've developed strong expertise in computer vision and machine learning, with a focus on industrial applications. At Orsan, I implemented a quality control system using OpenCV and TensorFlow that achieved 92% accuracy and reduced defects by 30%. My experience with real-time monitoring frameworks and U-Net algorithms directly aligns with the requirements mentioned in your job posting.\n\nWhat attracts me most to TechCorp is your commitment to advancing AI technology while maintaining a strong ethical framework. Your recent work on transparent AI systems particularly resonates with my belief that technology should be both powerful and accountable. I'm eager to contribute to a team that values innovation and responsible development.\n\nThank you for considering my application. I would welcome the opportunity to discuss how my background in machine learning and computer vision could contribute to TechCorp's ongoing success. I look forward to potentially joining your team and helping to develop the next generation of AI solutions.\n\nSincerely,"
}"""


class CoverLetterPrompt(BasePrompt):
    """Cover Letter prompt template."""

    def __init__(self):
        """Initialize the cover letter prompt template."""
        super().__init__(TEMPLATE)


COVER_LETTER_PROMPT = CoverLetterPrompt()
