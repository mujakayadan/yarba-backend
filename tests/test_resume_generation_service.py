"""Tests for resume generation service."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.models.resume import Resume
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.profile_repository import ProfileRepository
from core.repositories.resume_repository import ResumeRepository
from core.services.llm_service import LLMService
from core.services.resume_generation_service import ResumeGenerationService
from core.services.tex_service import TexService


@pytest.fixture
def mock_llm():
    """Create a mock LLM service."""
    llm = AsyncMock(spec=LLMService)
    llm.generate_section.return_value = "Generated content"
    llm.generate_cover_letter.return_value = "Generated cover letter"
    return llm


@pytest.fixture
def mock_tex_service():
    """Create a mock TeX service."""
    tex_service = AsyncMock(spec=TexService)
    tex_service.format_template.return_value = "Formatted TeX content"
    return tex_service


@pytest.fixture
def mock_profile_repository():
    """Create a mock profile repository."""
    repo = AsyncMock(spec=ProfileRepository)

    # Setup mock profile
    profile = Profile(
        user_id="test_user",
        name="Test User",
        email="test@example.com",
        phone="+1234567890",
        location="Test City",
        title="Software Engineer",
        summary="Experienced software engineer",
        links={
            "linkedin": "https://linkedin.com/in/testuser",
            "github": "https://github.com/testuser",
        },
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
        user_id="test_user",
        name="Test Portfolio",
        work_experience=[
            {
                "company": "Test Company",
                "position": "Software Engineer",
                "start_date": "2020-01-01",
                "end_date": "2022-01-01",
                "description": "Worked on test projects",
                "technologies": ["Python", "JavaScript"],
                "is_featured": True,
                "tags": ["backend", "frontend"],
            }
        ],
        education=[
            {
                "institution": "Test University",
                "degree": "B.S. Computer Science",
                "start_date": "2016-01-01",
                "end_date": "2020-01-01",
                "description": "Studied computer science",
                "is_featured": True,
                "tags": ["education"],
            }
        ],
        skills=[
            {"name": "Python", "level": 5, "category": "programming"},
            {"name": "JavaScript", "level": 4, "category": "programming"},
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
        user_id="test_user",
        name="Test Resume",
        profile_id="profile123",
        portfolio_id="portfolio123",
        sections=["summary", "work_experience", "education", "skills"],
        template_name="modern",
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
        tex_service=mock_tex_service,
        profile_repository=mock_profile_repository,
        portfolio_repository=mock_portfolio_repository,
        resume_repository=mock_resume_repository,
    )

    # Verify all dependencies are set
    assert service.llm == mock_llm
    assert service.tex == mock_tex_service
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
        user_id="test_user",
        resume_id="resume123",
        job_description="Test job description",
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
        tex_service=mock_tex_service,
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
