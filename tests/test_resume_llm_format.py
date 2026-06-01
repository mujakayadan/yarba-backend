"""Test for resume generation LLM formatting issue."""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

# Make sure tests can import from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.models.resume import Resume
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.profile_repository import ProfileRepository
from core.repositories.resume_repository import ResumeRepository
from core.repositories.user_repository import UserRepository
from core.services.llm_service import LLMService
from core.services.portfolio_service import PortfolioService
from core.services.profile_service import ProfileService
from core.services.prompt_service import PromptService
from core.services.resume_generation_service import ResumeGenerationService


@pytest.fixture
def user_id():
    """Get test user ID from settings."""
    return settings.test_user_id


@pytest.fixture
def mock_llm_response():
    """Create a mock LLM response."""
    return {
        "personal_information": {
            "full_name": "Test User",
            "title": "Software Engineer",
            "phone": "123-456-7890",
            "email": "test@example.com",
            "location": "New York, NY",
            "linkedin": "linkedin.com/in/testuser",
            "github": "github.com/testuser",
        },
        "career_summary": {
            "job_title": "Software Engineer",
            "years_of_experience": "5",
            "default_summary": "A Software Engineer with 5 years of experience in Python development.",
        },
        "skills": [
            {
                "category": "Programming Languages",
                "skills": [
                    "Python",
                    "JavaScript",
                    "TypeScript",
                    "SQL",
                    "Java",
                    "C++",
                    "Ruby",
                    "PHP",
                ],
            }
        ],
        "work_experience": [
            {
                "job_title": "Senior Software Engineer",
                "company": "Tech Co.",
                "location": "New York, NY",
                "time": "2020-01 - Present",
                "responsibilities": [
                    "Developed scalable backend services using Python and FastAPI",
                    "Implemented CI/CD pipelines for automated testing and deployment",
                    "Led a team of 3 junior developers",
                ],
            }
        ],
        "education": [
            {
                "degree_type": "Bachelor's",
                "degree": "Computer Science",
                "university_name": "Example University",
                "time": "2015 - 2019",
                "location": "Boston, MA",
                "GPA": "3.8",
                "transcript": [
                    "Algorithms and Data Structures",
                    "Software Engineering",
                    "Database Systems",
                    "Machine Learning",
                ],
            }
        ],
        "projects": [
            {
                "name": "Resume Builder",
                "bullet_points": [
                    "Developed a web application for creating resumes using FastAPI and React",
                    "Integrated with OpenAI API for content generation",
                    "Implemented LaTeX document generation for PDF output",
                ],
                "date": "2023",
            }
        ],
    }


@pytest.fixture
def portfolio_data():
    """Create sample portfolio data."""
    return {
        "personal_information": {
            "name": "Test User",
            "phone": "123-456-7890",
            "email": "test@example.com",
            "location": "New York, NY",
            "linkedin": "linkedin.com/in/testuser",
            "github": "github.com/testuser",
        },
        "skills": [
            {
                "category": "Programming Languages",
                "skills": [
                    "Python",
                    "JavaScript",
                    "TypeScript",
                    "SQL",
                    "Java",
                    "C++",
                    "Ruby",
                    "PHP",
                    "Go",
                    "Rust",
                ],
            },
            {
                "category": "Frameworks",
                "skills": [
                    "FastAPI",
                    "Django",
                    "Flask",
                    "React",
                    "Vue.js",
                    "Angular",
                    "Express",
                    "Spring Boot",
                ],
            },
        ],
        "work_experience": [
            {
                "title": "Senior Software Engineer",
                "company": "Tech Co.",
                "location": "New York, NY",
                "start_date": "2020-01",
                "end_date": "Present",
                "description": [
                    "Developed scalable backend services using Python and FastAPI",
                    "Implemented CI/CD pipelines for automated testing and deployment",
                    "Led a team of 3 junior developers",
                    "Optimized database queries for better performance",
                ],
            },
            {
                "title": "Software Engineer",
                "company": "Startup Inc.",
                "location": "San Francisco, CA",
                "start_date": "2018-03",
                "end_date": "2019-12",
                "description": [
                    "Developed RESTful APIs using Node.js and Express",
                    "Implemented authentication and authorization",
                    "Worked on frontend using React and Redux",
                ],
            },
        ],
        "education": [
            {
                "degree_type": "Bachelor's",
                "degree": "Computer Science",
                "institution": "Example University",
                "start_date": "2015",
                "end_date": "2019",
                "location": "Boston, MA",
                "gpa": "3.8",
                "courses": [
                    "Algorithms and Data Structures",
                    "Software Engineering",
                    "Database Systems",
                    "Machine Learning",
                    "Operating Systems",
                    "Computer Networks",
                ],
            }
        ],
        "projects": [
            {
                "name": "Resume Builder",
                "description": [
                    "Developed a web application for creating resumes using FastAPI and React",
                    "Integrated with OpenAI API for content generation",
                    "Implemented LaTeX document generation for PDF output",
                ],
                "date": "2023",
            },
            {
                "name": "E-commerce Platform",
                "description": [
                    "Built a full-stack e-commerce platform using MongoDB, Express, React, and Node.js",
                    "Implemented payment processing with Stripe",
                    "Created admin dashboard for managing products and orders",
                ],
                "date": "2022",
            },
        ],
    }


@pytest.fixture
def job_description():
    """Create a sample job description."""
    return """
    Software Engineer

    Company: Meriti Inc.
    Location: Remote, US

    Job Description:
    We are looking for a Software Engineer to join our growing team. You will be responsible for developing and maintaining web applications, implementing new features, and ensuring high performance and reliability of our systems.

    Requirements:
    - 3+ years of experience in software development
    - Proficiency in Python and JavaScript
    - Experience with web frameworks such as FastAPI, Django, or Flask
    - Familiarity with front-end technologies (React, Vue.js, or Angular)
    - Experience with databases (PostgreSQL, MongoDB)
    - Strong problem-solving skills
    - Excellent communication and teamwork abilities

    Nice to Have:
    - Experience with CI/CD pipelines
    - Knowledge of containerization (Docker, Kubernetes)
    - Experience with cloud platforms (AWS, GCP, Azure)

    Benefits:
    - Competitive salary
    - Flexible work hours
    - Remote work options
    - Health insurance
    - 401(k) plan
    - Professional development opportunities
    """


class MockAsyncResponse:
    """Mock response for AsyncMock."""

    def __init__(self, content):
        """Initialize with content."""
        self.choices = [
            type("Choice", (), {"message": type("Message", (), {"content": content})})
        ]


@pytest.fixture
def mock_repositories():
    """Create mock repositories."""
    resume_repo = AsyncMock(spec=ResumeRepository)
    portfolio_repo = AsyncMock(spec=PortfolioRepository)
    profile_repo = AsyncMock(spec=ProfileRepository)
    user_repo = AsyncMock(spec=UserRepository)

    # Set up portfolio data
    portfolio = MagicMock(spec=Portfolio)
    portfolio.model_dump.return_value = portfolio_data()
    portfolio_repo.get_by_id.return_value = portfolio
    portfolio_repo.get_by_user_id.return_value = portfolio

    # Set up profile data
    profile = MagicMock(spec=Profile)
    profile.id = PydanticObjectId()
    profile.preferences = MagicMock()
    profile_repo.get_by_id.return_value = profile
    profile_repo.get_by_user_id.return_value = profile

    # Set up resume data
    resume = MagicMock(spec=Resume)
    resume.id = PydanticObjectId()
    resume.user_id = PydanticObjectId()
    resume.profile_id = profile.id
    resume.portfolio_id = PydanticObjectId()
    resume.job_description = job_description()
    resume.company_name = "meriti_inc"
    resume.job_title = "software_engineer"
    resume_repo.get_by_id.return_value = resume

    return {
        "resume": resume_repo,
        "portfolio": portfolio_repo,
        "profile": profile_repo,
        "user": user_repo,
    }


@pytest.mark.asyncio
async def test_resume_variables_format(
    mock_repositories, mock_llm_response, job_description, portfolio_data
):
    """Test the format of variables passed to prompt service."""
    # Create an actual PromptService instance
    prompt_service = PromptService()

    # Mock the LLM service
    llm_service = AsyncMock(spec=LLMService)
    # Set up the LLM service to capture the prompt for inspection
    captured_prompt = None
    captured_system_prompt = None

    async def mock_get_completion(prompt, system_prompt, **kwargs):
        nonlocal captured_prompt, captured_system_prompt
        captured_prompt = prompt
        captured_system_prompt = system_prompt
        # Return JSON as a string to simulate LLM response
        return json.dumps(mock_llm_response)

    llm_service.get_completion.side_effect = mock_get_completion

    # Create services with real prompt service but mocked LLM service
    portfolio_service = PortfolioService(
        portfolio_repository=mock_repositories["portfolio"],
        user_repository=mock_repositories["user"],
    )

    profile_service = ProfileService(
        profile_repository=mock_repositories["profile"],
        user_repository=mock_repositories["user"],
    )

    # Create the resume generation service with our mocks
    resume_service = ResumeGenerationService(
        resume_repository=mock_repositories["resume"],
        portfolio_repository=mock_repositories["portfolio"],
        profile_repository=mock_repositories["profile"],
        profile_service=profile_service,
        portfolio_service=portfolio_service,
        llm_service=llm_service,
        prompt_service=prompt_service,
    )

    # Call the method that triggers the process
    resume_id = PydanticObjectId()
    await resume_service.generate_resume_content(resume_id)

    # Now we can check what was passed to the LLM service
    assert llm_service.get_completion.called, (
        "LLM service's get_completion method was not called"
    )

    # Log the captured prompt for inspection
    print("\n--- CAPTURED PROMPT ---")
    print(f"Length: {len(captured_prompt)}")
    print(f"First 500 chars: {captured_prompt[:500]}")
    print("--- END CAPTURED PROMPT ---\n")

    # Check that job description is included
    assert "job_description" in captured_prompt, "Job description not found in prompt"
    assert len(job_description) > 0 and job_description.strip() in captured_prompt, (
        "Job description content missing"
    )

    # Check that portfolio data is included
    assert "portfolio" in captured_prompt, "Portfolio not found in prompt"
    # Look for specific portfolio keys in the prompt
    keys_to_check = [
        "personal_information",
        "skills",
        "work_experience",
        "education",
        "projects",
    ]
    for key in keys_to_check:
        assert key in captured_prompt, f"Portfolio section '{key}' not found in prompt"

    # Verify the system prompt contains the right instructions
    assert "JSON" in captured_system_prompt, (
        "System prompt doesn't mention JSON output format"
    )

    # Test edge case: Check if our code handles empty job descriptions
    mock_repositories["resume"].get_by_id.return_value.job_description = ""

    # Create a new service with the empty job description
    resume_service_empty = ResumeGenerationService(
        resume_repository=mock_repositories["resume"],
        portfolio_repository=mock_repositories["portfolio"],
        profile_repository=mock_repositories["profile"],
        profile_service=profile_service,
        portfolio_service=portfolio_service,
        llm_service=llm_service,
        prompt_service=prompt_service,
    )

    # Reset captured variables
    captured_prompt = None
    captured_system_prompt = None

    # Try with empty job description
    try:
        await resume_service_empty.generate_resume_content(resume_id)
        # If we get here, check that we have appropriate handling
        assert captured_prompt is not None, (
            "LLM service should be called even with empty job description"
        )
    except ValueError as e:
        # Check if the error message is about missing job description
        assert "job description is required" in str(e).lower(), f"Unexpected error: {e}"


@pytest.mark.asyncio
async def test_collect_portfolio_data(mock_repositories, portfolio_data):
    """Test the _collect_portfolio_data method handles data correctly."""
    # Create services
    portfolio_service = PortfolioService(
        portfolio_repository=mock_repositories["portfolio"],
        user_repository=mock_repositories["user"],
    )

    profile_service = ProfileService(
        profile_repository=mock_repositories["profile"],
        user_repository=mock_repositories["user"],
    )

    # Mock the portfolio service methods
    async def mock_get_personal_info(user_id):
        return portfolio_data["personal_information"]

    profile_service.get_personal_information = AsyncMock(
        side_effect=mock_get_personal_info
    )

    # Create the resume generation service with our mocks
    resume_service = ResumeGenerationService(
        resume_repository=mock_repositories["resume"],
        portfolio_repository=mock_repositories["portfolio"],
        profile_repository=mock_repositories["profile"],
        profile_service=profile_service,
        portfolio_service=portfolio_service,
    )

    # Call the method directly
    resume = mock_repositories["resume"].get_by_id.return_value
    portfolio_data_result = await resume_service._collect_portfolio_data(resume)

    # Verify the data structure
    assert isinstance(portfolio_data_result, dict), (
        "Portfolio data should be a dictionary"
    )
    assert "personal_information" in portfolio_data_result, (
        "Personal information should be included"
    )
    assert "skills" in portfolio_data_result, "Skills should be included"
    assert "work_experience" in portfolio_data_result, (
        "Work experience should be included"
    )

    # Check that the data is properly converted to serializable format
    json_str = json.dumps(portfolio_data_result)
    assert len(json_str) > 0, "Portfolio data should be serializable to JSON"

    # Deserialize the JSON string to verify it's valid
    deserialized = json.loads(json_str)
    assert deserialized == portfolio_data_result, (
        "Serialized and deserialized data should match"
    )


@pytest.mark.asyncio
async def test_prompt_service_format_template(portfolio_data, job_description):
    """Test the PromptService._format_template method handles complex data correctly."""
    # Create the PromptService
    prompt_service = PromptService()

    # Create a simple template with portfolio and job description variables
    template = """
    Task: Create a resume based on the following data:

    Job Description:
    ${job_description}

    Portfolio:
    ${portfolio}
    """

    # Format the template with our test data
    variables = {"job_description": job_description, "portfolio": portfolio_data}

    formatted = prompt_service._format_template(template, variables)

    # Check that the job description is included correctly
    assert job_description in formatted, (
        "Job description should be included in formatted template"
    )

    # Check that portfolio sections are included
    for key in portfolio_data.keys():
        assert key in formatted, (
            f"Portfolio section '{key}' should be included in formatted template"
        )

    # Validate that the structure is preserved for complex nested objects
    assert '"category": "Programming Languages"' in formatted, (
        "Nested structure should be preserved"
    )

    # Validate that arrays are formatted correctly
    assert '"skills": [' in formatted, "Array formatting should be correct"

    # Check for serialization errors (common with ObjectId fields)
    assert "ObjectId(" not in formatted, "ObjectId should be serialized to string"
    assert "cannot be serialized" not in formatted, (
        "No serialization errors should be present"
    )
