"""Comprehensive prompt template for all resume sections."""

from typing import Dict, List

from .base_prompt import BasePrompt

TEMPLATE = """Task: Create a comprehensive resume by selecting and organizing the most relevant information from the candidate's portfolio to match the target job description.

CRITICAL INSTRUCTIONS:
- Use ONLY the information provided in the portfolio and profile data
- DO NOT invent, assume, or add any details not explicitly given
- If certain information is missing, do not fabricate it - work only with what is explicitly provided
- All content must be directly traceable to the provided data
- Each section must contain only verifiable information from the provided data
- You MUST return a valid JSON object as your response - no markdown formatting, no additional text
- Do not include "```json" or "```" markers in your response - only return the actual JSON object
- DO NOT return any arrays or objects as JSON-encoded strings. All arrays and objects must be native JSON arrays/objects, not strings. For example, "skills" must be an array, not a string containing JSON.

Instructions:
- Select and organize content from the portfolio based on relevance to the job description
- Format the selected information as a professional resume
- Focus on content most relevant to the target position
- Prioritize recent and significant experiences
- Quantify achievements with specific metrics where available
- Use appropriate JSON schema structure for each section before final LaTeX output
- Ensure all generated content aligns with the job description
- Format all dates and contact information consistently throughout

# PERSONAL INFORMATION SECTION
Use the following personal information from the profile data:
- Full name
- Contact details (phone, email, location)
- Relevant professional profiles (LinkedIn, GitHub, personal website)
Include only factual contact details explicitly provided - do not invent or assume any information.

# CAREER SUMMARY SECTION
Create a concise career summary description following these guidelines:
- The portfolio data may contain a list of job titles the user has held previously.
- SELECT ONE single job title from the portfolio that best matches the target position in the job description.
- This single selected job title should be provided as "job_title" in your response JSON.
- Your response JSON should also include a "default_summary" field.
- CRITICAL: The value for "default_summary" MUST ONLY contain the descriptive part of the summary. It should describe the candidate's expertise (e.g., "in Python development, machine learning, and computer vision.").
- DO NOT include the prefix "A [Job Title] with X years of experience" in the "default_summary" field value.
- DO NOT include the "years_of_experience" field in your JSON response; it will be added later from the database.
- The summary description should be between {{ preferences.career_summary.min_words }} and {{ preferences.career_summary.max_words }} words.
- Only reference skills, technologies, and experiences the candidate actually possesses.
- Use a professional tone.

# SKILLS SECTION
CRITICAL CONSTRAINTS FOR SKILLS (MUST BE FOLLOWED):
- You MUST select EXACTLY {{ preferences.skills.max_categories }} skill categories from the portfolio data below.
- Choose the categories most relevant to the Job Description.
- For EACH of the {{ preferences.skills.max_categories }} selected categories, you MUST include:
    - AT LEAST {{ preferences.skills.min_per_category }} skills.
    - NO MORE THAN {{ preferences.skills.max_per_category }} skills.
- Skills MUST be copied VERBATIM from the portfolio data. DO NOT ALTER THEM.

Detailed Instructions for Skills:
- First, identify the {{ preferences.skills.max_categories }} skill categories from the portfolio that are most relevant to the Job Description.
- From the chosen {{ preferences.skills.max_categories }} categories, select the most relevant skills within each category.
- Ensure you select enough skills to meet the minimum requirement of {{ preferences.skills.min_per_category }} per category. If a category has fewer than {{ preferences.skills.min_per_category }} skills listed in the portfolio, include ALL of them for that category.
- Do NOT exceed the maximum limit of {{ preferences.skills.max_per_category }} skills per category.
- Preserve the EXACT category names from the portfolio.
- Order the skills within each selected category by relevance to the Job Description.
- Do not split skills into different categories than they appear in the portfolio.

# WORK EXPERIENCE SECTION
Select the most relevant work experiences from the portfolio:
- CRITICAL: You MUST select EXACTLY {{ preferences.work_experience.max_jobs }} positions most relevant to the target job. If the portfolio contains FEWER than {{ preferences.work_experience.max_jobs }} jobs, you MUST include ALL available jobs. If the portfolio contains MORE than {{ preferences.work_experience.max_jobs }} jobs, select the {{ preferences.work_experience.max_jobs }} most relevant ones.
- For each position, include job title, company, location, and dates AS PROVIDED in the portfolio.
- Select EXACTLY {{ preferences.work_experience.bullet_points_per_job }} bullet points per role.
- CRITICAL: These bullet points MUST be copied VERBATIM from the portfolio data provided below. DO NOT summarize, rephrase, shorten, or modify the original bullet points in ANY WAY.
- Select the {{ preferences.work_experience.bullet_points_per_job }} bullet points that best demonstrate relevant skills and achievements for the target job, but COPY THEM EXACTLY as they are written in the portfolio.
- List positions in reverse chronological order (most recent first).

# EDUCATION SECTION
Select relevant education from the portfolio:
- CRITICAL: You MUST select EXACTLY {{ preferences.education.max_entries }} education entries most relevant to the target job. If the portfolio contains FEWER than {{ preferences.education.max_entries }} entries, you MUST include ALL available entries. If the portfolio contains MORE than {{ preferences.education.max_entries }} entries, select the {{ preferences.education.max_entries }} most relevant ones.
- Choose formal education and certifications relevant to the target position.
- Include degree name, institution, location, and graduation date EXACTLY as provided in the portfolio.
- Select EXACTLY {{ preferences.education.max_courses }} relevant courses or achievements if applicable.
- If fewer than {{ preferences.education.max_courses }} courses/achievements are listed for an entry in the portfolio, include ALL available ones for that entry.
- CRITICAL: DO NOT summarize, rephrase, or modify education details. Copy them VERBATIM from the portfolio data.
- CRITICAL: List education entries in REVERSE CHRONOLOGICAL order (most recent first).
- Do not assume degrees or certifications not explicitly mentioned.

# PROJECTS SECTION (if applicable)
Select relevant projects from the portfolio:
- IMPORTANT: Choose EXACTLY {{ preferences.project.max_projects }} projects most relevant to the target position.
- If fewer than {{ preferences.project.max_projects }} projects are available, include ALL available projects.
- If more than {{ preferences.project.max_projects }} projects are available, select the {{ preferences.project.max_projects }} most relevant ones.
- For each project, include name, role (if provided), and date EXACTLY as they appear in the portfolio.
- Select EXACTLY {{ preferences.project.bullet_points_per_project }} key bullet points for EACH project.
- CRITICAL: Project names, roles, dates, and bullet points MUST be copied VERBATIM from the portfolio data provided below. DO NOT summarize, rephrase, shorten, or modify them in ANY WAY.
- Select the {{ preferences.project.bullet_points_per_project }} bullet points that best demonstrate relevant skills, outcomes, or technical challenges, but COPY THEM EXACTLY.
- Select projects that demonstrate skills mentioned in the job description.
- Emphasize technologies used and quantifiable results (This applies to the original bullet points; do not change them).
- CRITICAL: YOU MUST INCLUDE {{ preferences.project.max_projects }} PROJECTS IN YOUR JSON RESPONSE (or all available projects if fewer than {{ preferences.project.max_projects }} exist).
- The JSON response MUST include a complete array with ALL selected projects up to the maximum number.

# PUBLICATIONS SECTION (if applicable)
Select relevant publications from the portfolio:
- IMPORTANT: Choose EXACTLY {{ preferences.publications.max_publications }} publications most relevant to the target position.
- If fewer than {{ preferences.publications.max_publications }} publications are available, include ALL available publications.
- If more than {{ preferences.publications.max_publications }} publications are available, select the {{ preferences.publications.max_publications }} most relevant ones.
- For each selected publication, include the full citation information (title, authors, journal/conference, date) EXACTLY as provided in the portfolio.
- CRITICAL: DO NOT summarize, rephrase, or modify the citation details. Copy them VERBATIM.
- Prioritize publications that demonstrate expertise in areas relevant to the job when selecting which to include.
- Include only verified publications with proper citations from the portfolio.

# AWARDS SECTION (if applicable)
CRITICAL CONSTRAINTS FOR AWARDS (MUST BE FOLLOWED):
- You MUST select EXACTLY {{ preferences.awards.max_awards }} awards from the portfolio data below.
- If the portfolio contains FEWER than {{ preferences.awards.max_awards }} awards, you MUST include ALL available awards.
- Award details (name, explanation, date if provided) MUST be copied VERBATIM from the portfolio data. DO NOT ALTER THEM.

Detailed Instructions for Awards:
- Select the {{ preferences.awards.max_awards }} awards that are most relevant to the Job Description.
- Copy the name, explanation, and date (if available) for each selected award EXACTLY as they appear in the portfolio.
- Do not summarize, rephrase, or modify the award details.
- Do not include awards not explicitly listed in the portfolio data.

Output Format:
Your response should be a single valid JSON object following the structure below.
IMPORTANT: Do not include any explanatory text, markdown formatting, code blocks, or any other content before or after the JSON.
The JSON should be properly formatted with correct quotes, commas, and brackets.
All text fields must be properly escaped JSON strings.
NOTE: Do NOT include years_of_experience in the career_summary object - it will be added from the user's portfolio.

Job Description:
{{ job_description }}

Portfolio Data:
{{ portfolio_data }}
"""


class ResumePrompt(BasePrompt):
    """Comprehensive resume prompt template combining all section prompts."""

    def __init__(self):
        """Initialize the comprehensive resume prompt template."""
        super().__init__(TEMPLATE)


RESUME_PROMPT = ResumePrompt()
