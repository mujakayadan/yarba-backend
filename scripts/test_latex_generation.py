"""Test script for the simplified LaTeX generation system."""

import asyncio
from pathlib import Path

from core.models.profile import PersonalInformation, Preferences, Profile
from core.models.resume import Resume
from core.services.latex_service import get_latex_service


async def test_resume_generation():
    """Test generating a resume PDF with the simplified LaTeX system."""
    # Create output directory if it doesn't exist
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    # Create personal information
    personal_info = PersonalInformation(
        full_name="John Doe",
        email="john.doe@example.com",
        phone="123-456-7890",
        address="New York, NY",
        linkedin="https://linkedin.com/in/johndoe",
        github="https://github.com/johndoe",
        website="https://johndoe.com",
    )

    # Create preferences with template settings
    preferences = Preferences()
    preferences.default_latex_templates = {
        "default_resume_template_id": "classic",
        "default_cover_letter_template_id": "standard",
    }

    # Create a profile
    profile = Profile(personal_information=personal_info, preferences=preferences)

    # Create a simple resume
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

    # Get the LaTeX service
    latex_service = get_latex_service()

    # Display available templates
    print("Available Resume Templates:")
    templates = latex_service.get_available_resume_templates()
    for template in templates:
        print(f"  - {template['id']}: {template['name']} - {template['description']}")

    # Generate LaTeX using the default template from profile
    print("\nGenerating LaTeX with default template...")
    latex_content = await latex_service.generate_resume_latex(resume, profile)

    # Save LaTeX to file for inspection
    latex_path = output_dir / "test_resume_default.tex"
    latex_path.write_text(latex_content)
    print(f"LaTeX saved to: {latex_path}")

    # Generate PDF
    print("Generating PDF...")
    pdf_content = await latex_service.compile_latex_to_pdf(latex_content)

    if pdf_content:
        # Save PDF to file
        pdf_path = output_dir / "test_resume_default.pdf"
        pdf_path.write_bytes(pdf_content)
        print(f"PDF saved to: {pdf_path}")
    else:
        print("PDF generation failed")

    # Test with explicit template selection
    if len(templates) > 1:
        # Use a different template than the default
        alt_template_id = next(
            (t["id"] for t in templates if t["id"] != "classic"), None
        )
        if alt_template_id:
            print(f"\nGenerating LaTeX with explicit template ({alt_template_id})...")
            latex_content = await latex_service.generate_resume_latex(
                resume, profile, template_id=alt_template_id
            )

            # Save LaTeX to file for inspection
            latex_path = output_dir / f"test_resume_{alt_template_id}.tex"
            latex_path.write_text(latex_content)
            print(f"LaTeX saved to: {latex_path}")

            # Generate PDF
            print("Generating PDF...")
            pdf_content = await latex_service.compile_latex_to_pdf(latex_content)

            if pdf_content:
                # Save PDF to file
                pdf_path = output_dir / f"test_resume_{alt_template_id}.pdf"
                pdf_path.write_bytes(pdf_content)
                print(f"PDF saved to: {pdf_path}")
            else:
                print("PDF generation failed")


async def test_cover_letter_generation():
    """Test generating a cover letter PDF with the simplified LaTeX system."""
    # This function would be implemented similarly to test_resume_generation
    # but for cover letters


if __name__ == "__main__":
    asyncio.run(test_resume_generation())
    # Uncomment to test cover letter generation
    # asyncio.run(test_cover_letter_generation())
