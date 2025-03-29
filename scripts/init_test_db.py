#!/usr/bin/env python
"""
Script to initialize a test database with sample data.
"""

import asyncio
import datetime
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from core.models.portfolio import CareerSummary, Portfolio, PortfolioItem
from core.models.preamble import Preamble
from core.models.profile import Preferences, Profile
from core.models.resume import Resume
from core.models.tex_header import TexHeader

# Import models
from core.models.user import User


async def init_test_db():
    """Initialize a test database with sample data."""
    # Load environment variables
    load_dotenv()

    # Get MongoDB connection details from environment
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    database_name = os.getenv("MONGODB_DATABASE", "rbt_test")

    logger.info(f"Connecting to MongoDB at {mongo_uri}")

    try:
        # Create Motor client
        client = AsyncIOMotorClient(mongo_uri)

        # Test connection
        await client.admin.command("ping")
        logger.info("Successfully connected to MongoDB")

        # Get database
        db = client[database_name]

        # Drop existing database if it exists
        if database_name in await client.list_database_names():
            logger.info(f"Dropping existing database: {database_name}")
            await client.drop_database(database_name)

        # Create collections
        logger.info("Creating collections...")
        await db.create_collection("users")
        await db.create_collection("profiles")
        await db.create_collection("portfolios")
        await db.create_collection("portfolio_items")
        await db.create_collection("resumes")
        await db.create_collection("preambles")
        await db.create_collection("tex_headers")

        # Create sample data
        logger.info("Creating sample data...")

        # Create a user
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # password: password
            is_active=True,
            is_superuser=False,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
        )
        await db.users.insert_one(user.model_dump())
        logger.info(f"Created user: {user.username}")

        # Create a profile
        profile = Profile(
            user_id=user.id,
            first_name="Test",
            last_name="User",
            email="test@example.com",
            phone="123-456-7890",
            location="New York, NY",
            website="https://example.com",
            github="https://github.com/testuser",
            linkedin="https://linkedin.com/in/testuser",
            twitter="https://twitter.com/testuser",
            bio="A test user for the resume builder application.",
            preferences=Preferences(
                project_details={
                    "show_description": True,
                    "show_url": True,
                    "show_technologies": True,
                    "show_date": True,
                },
                work_experience={
                    "show_description": True,
                    "show_location": True,
                    "show_date": True,
                },
                skills={
                    "show_level": True,
                    "show_years": True,
                    "group_by_category": True,
                },
                career_summary={"show_years_experience": True, "show_job_title": True},
                education={"show_gpa": True, "show_courses": True, "show_date": True},
                cover_letter={
                    "show_date": True,
                    "show_address": True,
                    "show_phone": True,
                    "show_email": True,
                },
                awards={"show_date": True, "show_issuer": True},
                publications={
                    "show_date": True,
                    "show_publisher": True,
                    "show_url": True,
                },
                feature_preferences={
                    "enable_ai_suggestions": True,
                    "enable_auto_save": True,
                    "enable_spell_check": True,
                    "enable_grammar_check": True,
                },
                notification_preferences={
                    "email_notifications": True,
                    "browser_notifications": True,
                },
                privacy_preferences={
                    "profile_visibility": "public",
                    "resume_visibility": "private",
                    "portfolio_visibility": "public",
                },
                llm_preferences={
                    "model_type": "Claude",
                    "model_name": "claude-3-5-sonnet-20240620",
                    "temperature": 0.1,
                    "p_value": 0.9,
                    "max_tokens": 4000,
                },
                section_preferences={
                    "sections_order": [
                        "personal_information",
                        "career_summary",
                        "work_experience",
                        "education",
                        "skills",
                        "projects",
                        "awards",
                        "publications",
                    ],
                    "visible_sections": [
                        "personal_information",
                        "career_summary",
                        "work_experience",
                        "education",
                        "skills",
                        "projects",
                    ],
                },
            ),
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
        )
        await db.profiles.insert_one(profile.model_dump())
        logger.info(f"Created profile for user: {user.username}")

        # Create a portfolio
        portfolio = Portfolio(
            user_id=user.id,
            title="My Portfolio",
            description="A collection of my work and experience.",
            professional_title="Software Engineer",
            career_summary=CareerSummary(
                job_titles=[
                    "Software Engineer",
                    "Full Stack Developer",
                    "Machine Learning Engineer",
                ],
                years_of_experience="5+",
                default_summary="in software development, machine learning, and computer vision.",
            ),
            theme="modern",
            layout="grid",
            items_per_page=10,
            is_public=True,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
        )
        await db.portfolios.insert_one(portfolio.model_dump())
        logger.info(f"Created portfolio for user: {user.username}")

        # Create portfolio items
        portfolio_items = [
            PortfolioItem(
                portfolio_id=portfolio.id,
                title="Resume Builder",
                description="A web application for creating and managing resumes.",
                type="project",
                url="https://github.com/testuser/resume-builder",
                image_url="https://example.com/images/resume-builder.png",
                technologies=["Python", "FastAPI", "MongoDB", "React"],
                tags=["web", "full-stack", "open-source"],
                date="2023-01-01",
                highlights=[
                    "Implemented a RESTful API using FastAPI",
                    "Designed a MongoDB database schema",
                    "Created a responsive UI with React",
                ],
                order=1,
                is_featured=True,
                metadata={"github_stars": 100, "github_forks": 20},
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow(),
            ),
            PortfolioItem(
                portfolio_id=portfolio.id,
                title="Software Engineer",
                description="Developed web applications and APIs for a SaaS company.",
                type="work_experience",
                company="Acme Inc.",
                location="New York, NY",
                start_date="2020-01-01",
                end_date="2023-01-01",
                technologies=["Python", "Django", "PostgreSQL", "AWS"],
                tags=["backend", "cloud", "api"],
                highlights=[
                    "Led a team of 5 developers",
                    "Reduced API response time by 50%",
                    "Implemented CI/CD pipelines",
                ],
                order=2,
                is_featured=True,
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow(),
            ),
            PortfolioItem(
                portfolio_id=portfolio.id,
                title="Bachelor of Science in Computer Science",
                description="Studied computer science with a focus on artificial intelligence.",
                type="education",
                institution="University of Example",
                location="Boston, MA",
                start_date="2016-09-01",
                end_date="2020-05-01",
                degree="Bachelor of Science",
                field_of_study="Computer Science",
                gpa="3.8",
                courses=[
                    "Data Structures",
                    "Algorithms",
                    "Machine Learning",
                    "Computer Vision",
                ],
                tags=["education", "computer-science", "ai"],
                highlights=[
                    "Graduated with honors",
                    "Published a paper on machine learning",
                    "Completed a thesis on computer vision",
                ],
                order=3,
                is_featured=True,
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow(),
            ),
        ]

        for item in portfolio_items:
            await db.portfolio_items.insert_one(item.model_dump())
        logger.info(f"Created {len(portfolio_items)} portfolio items")

        # Create a resume
        resume = Resume(
            user_id=user.id,
            profile_id=profile.id,
            portfolio_id=portfolio.id,
            title="My Resume",
            version=1,
            template_id="modern",
            company_name="Acme Inc.",
            job_title="Senior Software Engineer",
            job_description="Looking for a senior software engineer with experience in Python, FastAPI, and MongoDB.",
            content={
                "personal_information": {
                    "name": "Test User",
                    "email": "test@example.com",
                    "phone": "123-456-7890",
                    "location": "New York, NY",
                    "website": "https://example.com",
                    "github": "https://github.com/testuser",
                    "linkedin": "https://linkedin.com/in/testuser",
                },
                "career_summary": "A software engineer with 5+ years of experience in software development, machine learning, and computer vision.",
                "work_experience": [
                    {
                        "title": "Software Engineer",
                        "company": "Acme Inc.",
                        "location": "New York, NY",
                        "start_date": "2020-01-01",
                        "end_date": "2023-01-01",
                        "description": "Developed web applications and APIs for a SaaS company.",
                        "highlights": [
                            "Led a team of 5 developers",
                            "Reduced API response time by 50%",
                            "Implemented CI/CD pipelines",
                        ],
                    }
                ],
                "education": [
                    {
                        "institution": "University of Example",
                        "location": "Boston, MA",
                        "degree": "Bachelor of Science",
                        "field_of_study": "Computer Science",
                        "start_date": "2016-09-01",
                        "end_date": "2020-05-01",
                        "gpa": "3.8",
                        "courses": [
                            "Data Structures",
                            "Algorithms",
                            "Machine Learning",
                            "Computer Vision",
                        ],
                        "highlights": [
                            "Graduated with honors",
                            "Published a paper on machine learning",
                            "Completed a thesis on computer vision",
                        ],
                    }
                ],
                "skills": [
                    {"name": "Python", "level": "Expert", "years": 5},
                    {"name": "FastAPI", "level": "Advanced", "years": 3},
                    {"name": "MongoDB", "level": "Intermediate", "years": 2},
                    {"name": "React", "level": "Beginner", "years": 1},
                ],
                "projects": [
                    {
                        "title": "Resume Builder",
                        "description": "A web application for creating and managing resumes.",
                        "url": "https://github.com/testuser/resume-builder",
                        "technologies": ["Python", "FastAPI", "MongoDB", "React"],
                        "date": "2023-01-01",
                        "highlights": [
                            "Implemented a RESTful API using FastAPI",
                            "Designed a MongoDB database schema",
                            "Created a responsive UI with React",
                        ],
                    }
                ],
            },
            custom_sections=[
                {
                    "title": "Publications",
                    "items": [
                        {
                            "title": "Machine Learning in Practice",
                            "publisher": "Journal of AI",
                            "date": "2022-05-01",
                            "url": "https://example.com/publications/ml-in-practice",
                            "description": "A paper on practical applications of machine learning.",
                        }
                    ],
                }
            ],
            llm_settings={
                "model_type": "Claude",
                "model_name": "claude-3-5-sonnet-20240620",
                "temperature": 0.1,
                "p_value": 0.9,
                "max_tokens": 4000,
                "system_prompt_version": "v2.3",
            },
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
        )
        await db.resumes.insert_one(resume.model_dump())
        logger.info(f"Created resume for user: {user.username}")

        # Create LaTeX preambles
        preambles = [
            Preamble(
                name="default",
                type="resume_preamble",
                content="\\documentclass[letterpaper,11pt]{article}\n\\usepackage{latexsym}\n\\usepackage[empty]{fullpage}\n\\usepackage{titlesec}\n\\usepackage{marvosym}\n\\usepackage[usenames,dvipsnames]{color}\n\\usepackage{verbatim}\n\\usepackage{enumitem}\n\\usepackage[hidelinks]{hyperref}\n\\usepackage{fancyhdr}\n\\usepackage[english]{babel}\n\\usepackage{tabularx}\n\\usepackage{hyphenat}\n\\usepackage{fontawesome}\n\\usepackage{seqsplit}\n\\usepackage[T1]{fontenc}\n\\usepackage[utf8x]{inputenc}\n\\usepackage{lmodern,textcomp}\n\\usepackage{bookmark}",
                is_default=True,
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow(),
            ),
            Preamble(
                name="default",
                type="cover_letter_preamble",
                content="\\documentclass[11pt,a4paper]{letter}\n\\usepackage{fontspec}\n\\usepackage{xunicode}\n\\usepackage{xltxtra}\n\\usepackage{url}\n\\usepackage{parskip}\n\\usepackage[usenames,dvipsnames]{xcolor}\n\\usepackage{hyperref}\n\\usepackage{titlesec}\n\\usepackage{array}\n\\usepackage{enumitem}\n\\usepackage{geometry}\n\\usepackage{setspace}\n\\usepackage{fontawesome}\n\\usepackage{fancyhdr}\n\\usepackage{lastpage}\n\\usepackage{xltxtra}\n\\usepackage{microtype}\n\\usepackage{color}\n\\usepackage{hyphenat}\n\\usepackage{ragged2e}",
                is_default=True,
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow(),
            ),
        ]

        for preamble in preambles:
            await db.preambles.insert_one(preamble.model_dump())
        logger.info(f"Created {len(preambles)} LaTeX preambles")

        # Create TeX headers
        tex_headers = [
            TexHeader(
                name="modern",
                category="resume",
                content="\\pagestyle{fancy}\n\\fancyhf{} % clear all header and footer fields\n\\fancyfoot{}\n\\renewcommand{\\headrulewidth}{0pt}\n\\renewcommand{\\footrulewidth}{0pt}\n\n% Adjust margins\n\\addtolength{\\oddsidemargin}{-0.5in}\n\\addtolength{\\evensidemargin}{-0.5in}\n\\addtolength{\\textwidth}{1in}\n\\addtolength{\\topmargin}{-.5in}\n\\addtolength{\\textheight}{1.0in}\n\n\\urlstyle{same}\n\n\\raggedbottom\n\\raggedright\n\\setlength{\\tabcolsep}{0in}\n\\setlength{\\footskip}{4.08003pt}",
                is_default=True,
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow(),
            ),
            TexHeader(
                name="classic",
                category="resume",
                content="\\pagestyle{empty} % no page numbers\n\n% Adjust margins\n\\addtolength{\\oddsidemargin}{-0.5in}\n\\addtolength{\\evensidemargin}{-0.5in}\n\\addtolength{\\textwidth}{1in}\n\\addtolength{\\topmargin}{-0.5in}\n\\addtolength{\\textheight}{1.0in}\n\n\\raggedright\n\\raggedbottom\n\\renewcommand{\\arraystretch}{1.5}\n\\setlength{\\tabcolsep}{0in}",
                is_default=False,
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow(),
            ),
            TexHeader(
                name="default",
                category="cover_letter",
                content="\\geometry{left=1in,right=1in,top=1in,bottom=1in}\n\\setlength\\parindent{0pt}\n\\pagestyle{empty}\n\\setstretch{1.1}\n\\setlength{\\parskip}{8pt}\n\\hypersetup{colorlinks=true,urlcolor=blue}\n\\titleformat{\\section}{\\scshape\\raggedright\\large}{}{0em}{}\n\\titlespacing{\\section}{0pt}{10pt}{5pt}",
                is_default=True,
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow(),
            ),
        ]

        for tex_header in tex_headers:
            await db.tex_headers.insert_one(tex_header.model_dump())
        logger.info(f"Created {len(tex_headers)} TeX headers")

        # List collections
        collections = await db.list_collection_names()
        logger.info(f"Collections in {database_name} database: {collections}")

        # Count documents in each collection
        for collection in collections:
            count = await db[collection].count_documents({})
            logger.info(f"Collection {collection}: {count} documents")

        logger.info(f"Test database {database_name} initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize test database: {e}")
        return False


def main():
    """Run the script."""
    result = asyncio.run(init_test_db())
    if result:
        logger.info("Test database initialization completed successfully")
    else:
        logger.error("Test database initialization failed")


if __name__ == "__main__":
    main()
