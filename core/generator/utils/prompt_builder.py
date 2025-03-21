"""Prompt builder utilities for LLM-based content generation."""

from typing import Any, Dict, List, Optional

from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.models.resume import Resume


def build_resume_prompt(
    section_name: str,
    profile: Profile,
    resume: Resume,
    portfolio: Optional[Portfolio] = None,
    job_description: Optional[str] = None,
    job_title: Optional[str] = None,
    company_name: Optional[str] = None,
) -> str:
    """Build a prompt for generating resume section content.

    Args:
        section_name: Name of the section to generate
        profile: User profile
        resume: Resume to generate
        portfolio: Optional portfolio data
        job_description: Optional job description to tailor the content to
        job_title: Optional job title to tailor the content to
        company_name: Optional company name to tailor the content to

    Returns:
        str: Generated prompt
    """
    # Base prompt with system instructions
    prompt = f"""You are a professional resume writer with expertise in creating compelling, ATS-friendly content.
Your task is to generate content for the '{section_name}' section of a resume.

"""

    # Add job targeting information if available
    if job_title or company_name or job_description:
        prompt += "The resume is being tailored for "
        if job_title:
            prompt += f"a {job_title} position "
        if company_name:
            prompt += f"at {company_name} "
        prompt += "\n\n"

    if job_description:
        prompt += f"Job Description:\n{job_description}\n\n"

    # Add section-specific instructions
    section_instructions = {
        "personal_information": """Generate a professional personal information section for the resume.
Include the full name, email, phone number, and location. Optionally include LinkedIn, GitHub, and personal website if available.
Format the information in a clean, professional manner suitable for a resume header.""",
        "career_summary": """Generate a compelling career summary that highlights the candidate's experience, skills, and value proposition.
Keep it concise (3-5 sentences) and impactful, focusing on achievements and expertise relevant to the target position.
Avoid generic statements and use strong action verbs.""",
        "skills": """Generate a skills section organized by categories (e.g., Technical Skills, Soft Skills, Languages).
For each category, list relevant skills that match the job requirements and the candidate's experience.
Format the skills in a way that is easy to scan and ATS-friendly.""",
        "work_experience": """Generate work experience entries with the following format for each position:
- Company name, location
- Job title
- Employment dates (MM/YYYY - MM/YYYY or "Present" for current positions)
- 3-5 bullet points highlighting achievements, responsibilities, and impact
Use strong action verbs, quantify achievements where possible, and focus on results rather than just duties.""",
        "education": """Generate education entries with the following format for each institution:
- Institution name, location
- Degree and field of study
- Graduation date (MM/YYYY)
- Optional: GPA (if above 3.5), relevant coursework, academic achievements, extracurricular activities""",
        "projects": """Generate project entries with the following format for each project:
- Project name
- Technologies/tools used
- Brief description of the project's purpose and your role
- 2-3 bullet points highlighting your contributions, challenges overcome, and results achieved""",
        "awards": """Generate awards and honors entries with the following format:
- Award/honor name
- Issuing organization
- Date received (YYYY)
- Brief description of the award's significance""",
        "publications": """Generate publication entries with the following format:
- Title of publication
- Authors (if applicable)
- Journal/conference/publisher
- Publication date (YYYY)
- Brief description or impact of the publication""",
    }

    prompt += (
        section_instructions.get(
            section_name, f"Generate content for the {section_name} section."
        )
        + "\n\n"
    )

    # Add user information
    prompt += f"Candidate Information:\n"
    prompt += f"Name: {profile.full_name}\n"

    if portfolio:
        if portfolio.career_summary:
            prompt += (
                f"Experience: {portfolio.career_summary.years_of_experience} years\n"
            )
            prompt += f"Professional Title: {portfolio.get_appropriate_job_title()}\n"

        # Add relevant portfolio information based on section
        if section_name == "skills" and portfolio.skills:
            prompt += "\nSkill Categories:\n"
            for skill_category in portfolio.skills:
                for category, skills in skill_category.items():
                    prompt += f"- {category}: {', '.join(skills)}\n"

        elif section_name == "work_experience" and portfolio.work_experience:
            prompt += "\nWork Experience:\n"
            for exp in portfolio.work_experience:
                prompt += f"- {exp.company}, {exp.job_title}, {exp.time}\n"
                for resp in exp.responsibilities:
                    prompt += f"  * {resp}\n"

        elif section_name == "education" and portfolio.education:
            prompt += "\nEducation:\n"
            for edu in portfolio.education:
                prompt += f"- {edu.university_name}, {edu.degree_type} in {edu.degree}, {edu.time}\n"

        elif section_name == "projects" and portfolio.projects:
            prompt += "\nProjects:\n"
            for proj in portfolio.projects:
                prompt += f"- {proj.name}, {proj.date}\n"
                for point in proj.bullet_points:
                    prompt += f"  * {point}\n"

    # Final instructions
    prompt += f"""
Please generate professional, concise, and impactful content for the {section_name} section.
Format the response as a JSON object that can be directly used in the resume.
"""

    return prompt


def build_cover_letter_prompt(
    profile: Profile,
    resume: Resume,
    portfolio: Optional[Portfolio] = None,
    job_description: Optional[str] = None,
    job_title: Optional[str] = None,
    company_name: Optional[str] = None,
    recipient_name: Optional[str] = None,
    recipient_title: Optional[str] = None,
    recipient_company: Optional[str] = None,
    recipient_address: Optional[str] = None,
    paragraphs: int = 3,
) -> str:
    """Build a prompt for generating cover letter content.

    Args:
        profile: User profile
        resume: Resume to generate cover letter for
        portfolio: Optional portfolio data
        job_description: Optional job description to tailor the content to
        job_title: Optional job title to tailor the content to
        company_name: Optional company name to tailor the content to
        recipient_name: Optional name of the recipient
        recipient_title: Optional title of the recipient
        recipient_company: Optional company of the recipient
        recipient_address: Optional address of the recipient
        paragraphs: Number of paragraphs to generate (default: 3)

    Returns:
        str: Generated prompt
    """
    # Base prompt with system instructions
    prompt = """You are a professional cover letter writer with expertise in creating compelling, personalized cover letters.
Your task is to generate a cover letter that highlights the candidate's qualifications, experience, and enthusiasm for the position.

"""

    # Add job targeting information if available
    if job_title or company_name or job_description:
        prompt += "The cover letter is being tailored for "
        if job_title:
            prompt += f"a {job_title} position "
        if company_name:
            prompt += f"at {company_name} "
        prompt += "\n\n"

    if job_description:
        prompt += f"Job Description:\n{job_description}\n\n"

    # Add recipient information if available
    if recipient_name or recipient_title or recipient_company or recipient_address:
        prompt += "Recipient Information:\n"
        if recipient_name:
            prompt += f"Name: {recipient_name}\n"
        if recipient_title:
            prompt += f"Title: {recipient_title}\n"
        if recipient_company:
            prompt += f"Company: {recipient_company}\n"
        if recipient_address:
            prompt += f"Address: {recipient_address}\n"
        prompt += "\n"

    # Add candidate information
    prompt += f"Candidate Information:\n"
    prompt += f"Name: {profile.full_name}\n"
    prompt += f"Email: {profile.email}\n"
    if profile.phone:
        prompt += f"Phone: {profile.phone}\n"
    if profile.address:
        prompt += f"Address: {profile.address}\n"

    if portfolio:
        if portfolio.career_summary:
            prompt += (
                f"Experience: {portfolio.career_summary.years_of_experience} years\n"
            )
            prompt += f"Professional Title: {portfolio.get_appropriate_job_title()}\n"

        # Add key skills
        prompt += "\nKey Skills:\n"
        for skill in portfolio.get_skill_highlights():
            prompt += f"- {skill}\n"

        # Add work experience highlights
        if portfolio.work_experience:
            prompt += "\nWork Experience Highlights:\n"
            for exp in portfolio.work_experience[:2]:  # Limit to top 2 experiences
                prompt += f"- {exp.company}, {exp.job_title}, {exp.time}\n"
                for resp in exp.responsibilities[:2]:  # Limit to top 2 responsibilities
                    prompt += f"  * {resp}\n"

    # Structure and formatting instructions
    prompt += f"""
Cover Letter Structure:
1. Opening paragraph: Introduce yourself, state the position you're applying for, and how you learned about it.
2. Body paragraphs ({paragraphs-2} paragraphs): Highlight your relevant skills, experiences, and achievements that make you a good fit for the position.
3. Closing paragraph: Express enthusiasm for the opportunity, thank the recipient for their consideration, and include a call to action.

Please generate a professional, personalized cover letter that demonstrates the candidate's fit for the position.
The cover letter should be concise, engaging, and tailored to the specific job and company.
Format the response as a JSON object with the following structure:
{{
  "salutation": "Dear [Recipient Name/Title]",
  "content": "Full cover letter content with paragraphs separated by newlines",
  "closing": "Sincerely,\\n[Candidate Name]"
}}
"""

    return prompt
