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
Create a concise career summary following these guidelines:
- Select the most relevant job title from the candidate's history that best aligns with the target position
- Use the exact years of experience from the portfolio ( data.career_summary.years_of_experience )
- Create a summary between {{ preferences.career_summary.min_words }} and {{ preferences.career_summary.max_words }} words
- Only reference skills, technologies, and experiences the candidate actually has - do not fabricate or assume
- Use strong action verbs and quantify achievements where possible
- IMPORTANT: Start the summary with exactly "A [Job Title] with  data.career_summary.years_of_experience  years of experience in" followed by the candidate's expertise
- Use the {{ preferences.career_summary.tone }} tone
The career summary should highlight the candidate's unique value proposition for the role.

# SKILLS SECTION
IMPORTANT INSTRUCTIONS FOR SKILLS:
- PRESERVE the EXACT category names from the portfolio. Never rename, combine, or create new categories.
- Choose exactly the {{ preferences.skills.max_categories }} most relevant categories from the portfolio
- For EACH selected category, include EXACTLY {{ preferences.skills.min_skills_per_category }} to {{ preferences.skills.max_skills_per_category }} skills
- The minimum of {{ preferences.skills.min_skills_per_category }} skills per category is REQUIRED
- Select skills directly from each category in the portfolio, maintaining the original grouping
- Do NOT rename categories (e.g., don't change "Languages" to "Programming Languages")
- Prioritize skills mentioned in the job description
- Order skills within each category by relevance to the position
- Never split skills across different categories than they appear in the portfolio

# WORK EXPERIENCE SECTION
Select the most relevant work experiences from the portfolio:
- Choose the top {{ preferences.work_experience.max_jobs }} positions most relevant to the target job
- For each position, include job title, company, location, and dates
- Select {{ preferences.work_experience.bullet_points_per_job }} bullet points per role that best demonstrate relevant skills
- Focus on {{ preferences.work_experience.focus }} aspects of the work
- Prioritize experiences with quantifiable achievements
- List positions in reverse chronological order (most recent first)
- Use strong action verbs to begin bullet points

# EDUCATION SECTION
Select relevant education from the portfolio:
- Choose formal education and certifications relevant to the target position
- Include degree name, institution, location, and graduation date
- Select up to {{ preferences.education.max_courses }} relevant courses or achievements if applicable
- List education in reverse chronological order
- Do not assume degrees or certifications not explicitly mentioned

# PROJECTS SECTION (if applicable)
Select relevant projects from the portfolio:
- IMPORTANT: Choose EXACTLY {{ preferences.project.max_projects }} projects most relevant to the target position
- If fewer than {{ preferences.project.max_projects }} projects are available, include ALL available projects
- If more than {{ preferences.project.max_projects }} projects are available, select the {{ preferences.project.max_projects }} most relevant ones
- For each project, include name, role, and {{ preferences.project.bullet_points_per_project }} key bullet points
- IMPORTANT: Each project MUST have exactly {{ preferences.project.bullet_points_per_project }} bullet points
- Select projects that demonstrate skills mentioned in the job description
- Prioritize projects with measurable outcomes or technical challenges overcome
- Emphasize technologies used and quantifiable results
- CRITICAL: YOU MUST INCLUDE {{ preferences.project.max_projects }} PROJECTS IN YOUR JSON RESPONSE (or all available projects if fewer than {{ preferences.project.max_projects }} exist)
- The JSON response MUST include a complete array with ALL projects up to the maximum number

# PUBLICATIONS SECTION (if applicable)
Select relevant publications from the portfolio:
- Choose up to {{ preferences.publications.max_publications }} publications most relevant to the target position
- Include full citation information (title, authors, journal/conference, date)
- Prioritize publications that demonstrate expertise in areas relevant to the job
- Include only verified publications with proper citations

# AWARDS AND HONORS SECTION (if applicable)
Select relevant awards from the portfolio:
- Choose up to {{ preferences.awards.max_awards }} awards or recognitions relevant to the target position
- Include award name, granting organization, and date
- Prioritize awards that demonstrate excellence in areas relevant to the job
- Do not include awards not explicitly mentioned in the portfolio

Output Format:
Your response should be a single valid JSON object following the structure below.
IMPORTANT: Do not include any explanatory text, markdown formatting, code blocks, or any other content before or after the JSON.
The JSON should be properly formatted with correct quotes, commas, and brackets.
All text fields must be properly escaped JSON strings.

JSON Structure:
{
  "personal_information": {
    "full_name": "/* FULL_NAME */",
    "title": "/* SELECTED_JOB_TITLE */",
    "phone": "/* PHONE_NUMBER */",
    "email": "/* EMAIL_ADDRESS */",
    "location": "/* LOCATION */",
    "linkedin": "/* LINKEDIN_URL */",
    "github": "/* GITHUB_URL */"
  },
  "career_summary": {
    "job_title": "/* SELECTED_JOB_TITLE */",
    "years_of_experience": "data.career_summary.years_of_experience",
    "default_summary": "/* CAREER_SUMMARY_TEXT */"
  },
  "skills": [
    {
      "category": "/* SKILL_CATEGORY_1 */",
      "skills": ["/* SKILL_1 */", "/* SKILL_2 */", "/* SKILL_3 */", "/* SKILL_4 */", "/* SKILL_5 */", "/* SKILL_6 */", "/* SKILL_7 */", "/* SKILL_8 */"]
    },
    {
      "category": "/* SKILL_CATEGORY_2 */",
      "skills": ["/* SKILL_1 */", "/* SKILL_2 */", "/* SKILL_3 */", "/* SKILL_4 */", "/* SKILL_5 */", "/* SKILL_6 */", "/* SKILL_7 */", "/* SKILL_8 */"]
    }
  ],
  "work_experience": [
    {
      "job_title": "/* JOB_TITLE */",
      "company": "/* COMPANY_NAME */",
      "location": "/* LOCATION */",
      "time": "/* START_DATE */ - /* END_DATE */",
      "responsibilities": [
        "/* ACHIEVEMENT_1_WITH_METRICS */",
        "/* ACHIEVEMENT_2_WITH_METRICS */"
      ]
    }
  ], // IMPORTANT: Include EXACTLY {{ preferences.work_experience.max_jobs }} work experiences, or all available if fewer
  "education": [
    {
      "degree_type": "/* DEGREE_TYPE */",
      "degree": "/* DEGREE_NAME */",
      "university_name": "/* INSTITUTION_NAME */",
      "time": "/* START_YEAR */ - /* END_YEAR */",
      "location": "/* LOCATION */",
      "GPA": "/* GPA */",
      "transcript": [
        "/* COURSE_1 */",
        "/* COURSE_2 */"
      ]
    }
  ],
  "projects": [
    {
      "name": "PROJECT_NAME_1",
      "date": "DATE",
      "bullet_points": [
        "BULLET_POINT_1",
        "BULLET_POINT_2",
        "BULLET_POINT_3"
      ]
    },
    {
      "name": "PROJECT_NAME_2",
      "date": "DATE",
      "bullet_points": [
        "BULLET_POINT_1",
        "BULLET_POINT_2",
        "BULLET_POINT_3"
      ]
    },
    {
      "name": "PROJECT_NAME_3",
      "date": "DATE",
      "bullet_points": [
        "BULLET_POINT_1",
        "BULLET_POINT_2",
        "BULLET_POINT_3"
      ]
    },
    {
      "name": "PROJECT_NAME_4",
      "date": "DATE",
      "bullet_points": [
        "BULLET_POINT_1",
        "BULLET_POINT_2",
        "BULLET_POINT_3"
      ]
    },
    {
      "name": "PROJECT_NAME_5",
      "date": "DATE",
      "bullet_points": [
        "BULLET_POINT_1",
        "BULLET_POINT_2",
        "BULLET_POINT_3"
      ]
    }
  ], // IMPORTANT: Include EXACTLY {{ preferences.project.max_projects }} projects, or all available if fewer
  "publications": [
    {
      "name": "/* PUBLICATION_TITLE */",
      "publisher": "/* JOURNAL_OR_CONFERENCE */",
      "link": "/* PUBLICATION_LINK */",
      "time": "/* MONTH */, /* YEAR */"
    }
  ],
  "awards": [
    {
      "name": "/* AWARD_NAME */",
      "explanation": "/* AWARD_EXPLANATION */"
    }
  ]
}

Job Description:
{{ job_description }}

Resume Data:
{{ data }}
"""


class ResumePrompt(BasePrompt):
    """Comprehensive resume prompt template combining all section prompts."""

    def __init__(self):
        """Initialize the comprehensive resume prompt template."""
        super().__init__(TEMPLATE)


RESUME_PROMPT = ResumePrompt()
