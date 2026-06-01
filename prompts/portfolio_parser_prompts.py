"""Prompts related to portfolio parsing and generation."""

from prompts.base_prompt import BasePrompt

MAP_TEXT_TO_PORTFOLIO_TEMPLATE = """
You are an expert resume and portfolio parser. You will be given the raw text content extracted
from a document (likely a resume or CV).
Your task is to analyze this text, identify relevant sections and information, and structure it
according to the Portfolio JSON schema provided by the system.

Input Document Text:
```text
{{ document_text }}
```

Please extract and structure the information to populate the fields of the Portfolio model.
Focus on identifying and extracting data for the following typical resume/CV sections:
- Career Summary / Professional Summary / Objective
- Contact Information (though this might be handled separately, be aware if it's present)
- Skills (try to categorize them if possible, e.g., technical skills, soft skills, languages)
- Work Experience (job title, company name, employment dates, location, key responsibilities, achievements)
- Education (degree name, major, institution name, graduation dates, location, GPA if mentioned, relevant coursework)
- Projects (project name, description, technologies used, your role, links if available)
- Awards and Recognitions (name of award, issuing organization, date)
- Publications (title, authors, journal/conference, date, DOI/link if available)
- Certifications (name of certification, issuing body, date obtained)
- References (usually stated as "available upon request" - note if present, but detailed references are rare)
- Custom Sections (be prepared for other section titles the user might have, like "Interests", "Volunteering")

**CRITICAL INSTRUCTIONS FOR URL/LINK FIELDS:**
- ONLY include the "link" field if you find an actual, valid URL in the document (starting with http:// or https://)
- If you find text that looks like a domain but lacks protocol (e.g., "github.com/user"), add "https://" to make it valid
- If NO URL is found for a project or publication, DO NOT include the "link" field in the JSON at all - completely omit it
- NEVER use placeholder text like "[link]", "[url]", "(link)", "<link>", "{link}", "N/A", "TBD", or any similar placeholders
- NEVER create fake or placeholder URLs - only use actual URLs found in the document
- If uncertain whether text is a URL, err on the side of omitting the link field entirely

Ensure your output strictly adheres to the target Portfolio JSON schema that the system will use to validate your response.
If information for a specific field is not found in the document, omit that field or use a default empty value
(e.g., an empty list `[]` for list-based fields, an empty string `""` for optional string fields, or `null` if appropriate by the schema)
as defined by the Portfolio model structure.

Pay attention to dates and try to parse them into a consistent format if possible (e.g., YYYY-MM-DD or YYYY-MM).
For work experience and education, correctly associate descriptions, responsibilities, and achievements with the respective entries.
Be mindful of context when extracting information. The same text might mean different things in different sections.
Output ONLY the JSON object representing the Portfolio.
"""


class MapDocumentToPortfolioPrompt(BasePrompt):
    """Prompt to instruct an LLM to map raw text extracted from a document
    to the Portfolio Pydantic model schema.
    """

    def __init__(self):
        super().__init__(template=MAP_TEXT_TO_PORTFOLIO_TEMPLATE)

    def format(self, document_text: str) -> str:
        """Formats the prompt with the provided document text."""
        return super().format(document_text=document_text)


# Example usage (for testing this prompt class):
# if __name__ == "__main__":
#     sample_text_input = """
# John Doe
# Software Engineer
# johndoe@email.com | (555) 123-4567 | linkedin.com/in/johndoe
#
# Summary
# Highly skilled Software Engineer with 5+ years of experience...
#
# Experience
# Tech Solutions Inc. - Senior Software Engineer (Jan 2020 - Present)
# - Developed and maintained web applications using Python and Django.
# - Led a team of 3 junior developers.
#
# Education
# University of Advanced Technology - M.S. in Computer Science (2018 - 2020)
# - GPA: 3.9/4.0
#
# Skills
# Python, Django, JavaScript, React, Docker, AWS
# """
#     prompt_instance = MapDocumentToPortfolioPrompt()
#     formatted_prompt = prompt_instance.format(document_text=sample_text_input)
#     print(formatted_prompt)
