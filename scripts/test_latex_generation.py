"""Test script for the simplified LaTeX generation system."""

import asyncio
import json
import os
from pathlib import Path

from core.models.profile import Profile
from core.models.resume import Resume
from core.services.latex_service import get_latex_service


async def test_resume_generation():
    """Test generating a resume PDF with the simplified LaTeX system."""
    # Create output directory if it doesn't exist
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # Create a simple resume and profile
    resume = Resume(
        title="Test Resume",
        content={
            "personal_information": {
                "full_name": "John Doe",
                "email": "john.doe@example.com",
                "phone": "123-456-7890",
                "address": "New York, NY",
                "linkedIn": "https://linkedin.com/in/johndoe",
                "gitHub": "https://github.com/johndoe",
                "website": "https://johndoe.com",
            },
            "career_summary": {
                "job_title": "Software Engineer",
                "years_of_experience": "5",
                "career_summary": "specializing in backend development with Python and FastAPI.",
            },
            "skills": [
                {
                    "category": "Programming Languages",
                    "skills": "Python, JavaScript, TypeScript, SQL",
                },
                {"category": "Frameworks", "skills": "FastAPI, Express, React, Django"},
                {"category": "Tools", "skills": "Git, Docker, AWS, MongoDB"},
            ],
            "work_experience": [
                {
                    "job_title": "Senior Software Engineer",
                    "company": "Tech Solutions Inc.",
                    "location": "New York, NY",
                    "time": "Jan 2020 - Present",
                    "responsibilities": [
                        "Developed scalable API endpoints using FastAPI",
                        "Implemented CI/CD pipelines using GitHub Actions",
                        "Optimized MongoDB queries, improving performance by 40%",
                    ],
                },
                {
                    "job_title": "Software Engineer",
                    "company": "WebDev Co.",
                    "location": "Boston, MA",
                    "time": "Jun 2017 - Dec 2019",
                    "responsibilities": [
                        "Built RESTful APIs using Node.js and Express",
                        "Developed front-end components with React",
                        "Implemented automated testing with Jest",
                    ],
                },
            ],
            "education": [
                {
                    "university": "Massachusetts Institute of Technology",
                    "location": "Cambridge, MA",
                    "degree": "B.S. Computer Science",
                    "time": "2013 - 2017",
                    "key_courses": "Algorithms, Data Structures, Machine Learning, Databases",
                }
            ],
            "projects": [
                {
                    "name_and_tech": "Personal Finance Tracker (Python, FastAPI, React)",
                    "date": "2022",
                    "bullet_points": [
                        "Created a personal finance tracking app with data visualization",
                        "Implemented secure authentication with JWT",
                        "Deployed on AWS with Terraform for infrastructure as code",
                    ],
                }
            ],
        },
    )

    profile = Profile(
        personal_information={
            "full_name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "123-456-7890",
            "address": "New York, NY",
        }
    )

    # Get the LaTeX service
    latex_service = get_latex_service()

    # Generate LaTeX
    print("Generating LaTeX...")
    latex_content = await latex_service.generate_resume_latex(resume, profile)

    # Save LaTeX to file for inspection
    latex_path = output_dir / "test_resume.tex"
    latex_path.write_text(latex_content)
    print(f"LaTeX saved to: {latex_path}")

    # Generate PDF
    print("Generating PDF...")
    pdf_content = await latex_service.compile_latex_to_pdf(latex_content)

    if pdf_content:
        # Save PDF to file
        pdf_path = output_dir / "test_resume.pdf"
        pdf_path.write_bytes(pdf_content)
        print(f"PDF saved to: {pdf_path}")
    else:
        print("PDF generation failed")


if __name__ == "__main__":
    asyncio.run(test_resume_generation())
