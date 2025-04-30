"""Tests for resume generation service."""

from unittest.mock import AsyncMock

import pytest
from beanie import PydanticObjectId
from pydantic import EmailStr

from core.models import Education, Skill, WorkExperience
from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.models.resume import Resume
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.profile_repository import ProfileRepository
from core.repositories.resume_repository import ResumeRepository
from core.services.llm_service import LLMService
from core.services.resume_generation_service import ResumeGenerationService


@pytest.fixture
def mock_llm():
    """Create a mock LLM service."""
    llm = AsyncMock(spec=LLMService)
    llm.generate_section.return_value = "Generated content"
    llm.generate_cover_letter.return_value = "Generated cover letter"
    return llm


@pytest.fixture
def mock_profile_repository():
    """Create a mock profile repository."""
    repo = AsyncMock(spec=ProfileRepository)

    # Setup mock profile
    profile = Profile(
        user_id=PydanticObjectId("test_user"),
        full_name="Test User",
        email=EmailStr(),
        phone="+1234567890",
        address="Test City",
        linkedin="https://linkedin.com/in/testuser",
        github="https://github.com/testuser",
        life_story="Experienced software engineer",
    )

    repo.get_by_id.return_value = profile
    repo.get_by_user_id.return_value = profile
    return repo


@pytest.fixture
def mock_portfolio_repository():
    """Create a mock portfolio repository."""
    repo = AsyncMock(spec=PortfolioRepository)

    # Setup mock portfolio
    portfolio = Portfolio(
        user_id=PydanticObjectId("test_user"),
        work_experience=[
            WorkExperience(
                job_title="Test Job Title",
                company="Test Company",
                location="Test Location",
                time="time",
                responsibilities=["Test Responsibilities 1", "Test Responsibilities 2"],
            )
        ],
        education=[
            Education(
                degree_type="B.S.",
                degree="Computer Science",
                university_name="Test University",
                time="2016-2020",
                location="Test Location",
                GPA="3.8",
                transcript=["Computer Science 101", "Data Structures", "Algorithms"],
            )
        ],
        skills=[
            Skill(category="programming", skills=["Python", "JavaScript"]),
            Skill(category="databases", skills=["MongoDB", "PostgreSQL"]),
            Skill(category="frameworks", skills=["FastAPI", "Django"]),
        ],
    )

    repo.get_by_id.return_value = portfolio
    repo.get_by_user_id.return_value = portfolio
    return repo


@pytest.fixture
def mock_resume_repository():
    """Create a mock resume repository."""
    repo = AsyncMock(spec=ResumeRepository)

    # Setup mock resume
    resume = Resume(
        user_id=PydanticObjectId("test_user"),
        profile_id=PydanticObjectId("profile123"),
        portfolio_id=PydanticObjectId("portfolio123"),
        template_id="modern",
        content={
            "summary": "Test summary",
            "work_experience": "Test work experience",
            "education": "Test education",
            "skills": "Test skills",
        },
    )

    repo.get_by_id.return_value = resume
    repo.save.return_value = resume
    return repo


@pytest.mark.asyncio
async def test_generation_service_init(
    mock_llm,
    mock_tex_service,
    mock_profile_repository,
    mock_portfolio_repository,
    mock_resume_repository,
):
    """Test resume generation service initialization."""
    # Create service with all dependencies
    service = ResumeGenerationService(
        llm_service=mock_llm,
        latex_service=mock_tex_service,
        profile_repository=mock_profile_repository,
        portfolio_repository=mock_portfolio_repository,
        resume_repository=mock_resume_repository,
    )

    # Verify all dependencies are set
    assert service.llm_service == mock_llm
    assert service.latex_service == mock_tex_service
    assert service.profile_repository == mock_profile_repository
    assert service.portfolio_repository == mock_portfolio_repository
    assert service.resume_repository == mock_resume_repository


@pytest.mark.asyncio
async def test_generate_resume_content(
    mock_llm, mock_profile_repository, mock_portfolio_repository, mock_resume_repository
):
    """Test generating resume content."""
    # Create service
    service = ResumeGenerationService(
        llm_service=mock_llm,
        profile_repository=mock_profile_repository,
        portfolio_repository=mock_portfolio_repository,
        resume_repository=mock_resume_repository,
    )

    # Test generate resume content
    result = await service.generate_resume_content(
        resume_id=PydanticObjectId("resume123"),
        regenerate_sections=["Test job description"],
    )

    # Verify repositories were called
    mock_resume_repository.get_by_id.assert_called_once_with("resume123")
    mock_profile_repository.get_by_id.assert_called_once()
    mock_portfolio_repository.get_by_id.assert_called_once()

    # Verify LLM was configured for user
    mock_llm.configure_for_user.assert_called_once_with("test_user")

    # Verify content was generated for each section
    assert mock_llm.generate_section.call_count == 4

    # Verify result has content for each section
    assert "summary" in result
    assert "work_experience" in result
    assert "education" in result
    assert "skills" in result
    assert result["summary"] == "Generated content"


@pytest.mark.asyncio
async def test_generate_cover_letter(
    mock_llm, mock_tex_service, mock_profile_repository, mock_resume_repository
):
    """Test generating cover letter."""
    # Create service
    service = ResumeGenerationService(
        llm_service=mock_llm,
        latex_service=mock_tex_service,
        profile_repository=mock_profile_repository,
        resume_repository=mock_resume_repository,
    )

    # Test generate cover letter
    result = await service.generate_cover_letter(
        user_id="test_user",
        resume_id="resume123",
        job_description="Test job description",
        company_name="Test Company",
        job_title="Test Job",
    )

    # Verify LLM was configured for user
    mock_llm.configure_for_user.assert_called_once_with("test_user")

    # Verify LLM generate_cover_letter was called
    mock_llm.generate_cover_letter.assert_called_once()

    # Verify TeX service was used to format the letter
    mock_tex_service.format_template.assert_called_once()

    # Verify result
    assert result == "Formatted TeX content"


@pytest.mark.asyncio
async def test_generate_complete_resume(
    mock_resume, mock_profile, mock_portfolio, mock_llm
):
    """Test generate_complete_resume functionality."""

    # Mock repositories
    resume_repo = AsyncMock(spec=ResumeRepository)
    profile_repo = AsyncMock(spec=ProfileRepository)
    portfolio_repo = AsyncMock(spec=PortfolioRepository)

    # Set up mock returns
    resume_repo.get_by_id.return_value = mock_resume
    profile_repo.get_by_id.return_value = mock_profile
    portfolio_repo.get_by_id.return_value = mock_portfolio

    # Mock LLM response
    mock_llm.get_completion.return_value = """
    {
        "personal_information": {
            "full_name": "John Doe",
            "title": "Software Engineer",
            "phone": "123-456-7890",
            "email": "john@example.com",
            "location": "New York, NY",
            "linkedin": "linkedin.com/in/johndoe",
            "github": "github.com/johndoe"
        },
        "career_summary": {
            "job_title": "Software Engineer",
            "years_of_experience": "5",
            "default_summary": "A Software Engineer with 5 years of experience in web development."
        },
        "skills": [
            {
                "category": "Programming Languages",
                "skills": ["Python", "JavaScript", "TypeScript", "Java"]
            }
        ]
    }
    """

    # Initialize service with mocks
    service = ResumeGenerationService(
        resume_repository=resume_repo,
        portfolio_repository=portfolio_repo,
        profile_repository=profile_repo,
        llm_service=mock_llm,
    )

    # Call the method under test
    result = await service.generate_complete_resume(mock_resume.id)

    # Assertions
    resume_repo.get_by_id.assert_called_once_with(mock_resume.id)
    profile_repo.get_by_id.assert_called_once()
    mock_llm.get_completion.assert_called_once()
    resume_repo.update.assert_called_once()

    # Check that result contains expected structure
    assert "personal_information" in result
    assert "career_summary" in result
    assert "skills" in result

    # Verify the mock resume has been updated
    assert mock_resume.content is not None
    assert isinstance(mock_resume.content, dict)
