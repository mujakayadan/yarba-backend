"""Test configuration for pytest."""

import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.dependencies.database import (
    get_portfolio_repository,
    get_profile_repository,
    get_resume_repository,
    get_user_repository,
)
from api.main import app as fastapi_app
from api.middleware.auth import get_current_user
from core.models.portfolio import Portfolio
from core.models.profile import Profile
from core.models.resume import Resume
from core.models.user import User
from core.repositories.portfolio_repository import PortfolioRepository
from core.repositories.profile_repository import ProfileRepository
from core.repositories.resume_repository import ResumeRepository
from core.repositories.user_repository import UserRepository
from core.services.auth_service import AuthService
from core.services.latex_service import LatexService
from core.services.llm_service import LLMService
from core.services.prompt_service import PromptService
from core.services.resume_generation_service import ResumeGenerationService
from core.services.resume_service import ResumeService


@pytest.fixture
def app():
    """Create a FastAPI app for testing."""
    return fastapi_app


@pytest.fixture
def client(app):
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_database():
    """Fixture for mocking MongoDB database."""
    db = AsyncMock()

    # Mock collections
    db.users = AsyncMock()
    db.users.find_one = AsyncMock()
    db.users.insert_one = AsyncMock()
    db.users.update_one = AsyncMock()
    db.users.delete_one = AsyncMock()
    db.users.find = AsyncMock()

    db.profiles = AsyncMock()
    db.profiles.find_one = AsyncMock()
    db.profiles.insert_one = AsyncMock()
    db.profiles.update_one = AsyncMock()
    db.profiles.delete_one = AsyncMock()
    db.profiles.find = AsyncMock()

    db.portfolios = AsyncMock()
    db.portfolios.find_one = AsyncMock()
    db.portfolios.insert_one = AsyncMock()
    db.portfolios.update_one = AsyncMock()
    db.portfolios.delete_one = AsyncMock()
    db.portfolios.find = AsyncMock()

    db.resumes = AsyncMock()
    db.resumes.find_one = AsyncMock()
    db.resumes.insert_one = AsyncMock()
    db.resumes.update_one = AsyncMock()
    db.resumes.delete_one = AsyncMock()
    db.resumes.find = AsyncMock()

    db.tex_headers = AsyncMock()
    db.tex_headers.find_one = AsyncMock()
    db.tex_headers.insert_one = AsyncMock()
    db.tex_headers.update_one = AsyncMock()
    db.tex_headers.delete_one = AsyncMock()
    db.tex_headers.find = AsyncMock()

    return db


@pytest.fixture
def mock_user_repository():
    """Fixture for mocking user repository."""
    repository = AsyncMock(spec=UserRepository)
    repository.get_by_email = AsyncMock()
    repository.create = AsyncMock()
    repository.get_by_id = AsyncMock()
    repository.update = AsyncMock()
    repository.delete = AsyncMock()
    return repository


@pytest.fixture
def mock_profile_repository():
    """Fixture for mocking profile repository."""
    repository = AsyncMock(spec=ProfileRepository)
    repository.get_by_id = AsyncMock()
    repository.get_by_user_id = AsyncMock()
    repository.create = AsyncMock()
    repository.update = AsyncMock()
    repository.delete = AsyncMock()
    return repository


@pytest.fixture
def mock_portfolio_repository():
    """Fixture for mocking portfolio repository."""
    repository = AsyncMock(spec=PortfolioRepository)
    repository.get_by_id = AsyncMock()
    repository.get_by_user_id = AsyncMock()
    repository.create = AsyncMock()
    repository.update = AsyncMock()
    repository.delete = AsyncMock()
    return repository


@pytest.fixture
def mock_resume_repository():
    """Fixture for mocking resume repository."""
    repository = AsyncMock(spec=ResumeRepository)
    repository.get_by_id = AsyncMock()
    repository.get_all_by_user_id = AsyncMock()
    repository.create = AsyncMock()
    repository.update = AsyncMock()
    repository.delete = AsyncMock()
    return repository


@pytest.fixture
def mock_auth_service(mock_user_repository):
    """Fixture for mocking auth service."""
    service = AsyncMock(spec=AuthService)
    service.register_user = AsyncMock()
    service.authenticate_user = AsyncMock()
    service.create_access_token = AsyncMock()
    service.verify_token = AsyncMock()
    service.user_repository = mock_user_repository
    return service


@pytest.fixture
def mock_resume_service(mock_resume_repository):
    """Fixture for mocking resume service."""
    service = AsyncMock(spec=ResumeService)
    service.create_resume = AsyncMock()
    service.get_resume = AsyncMock()
    service.get_all_resumes = AsyncMock()
    service.update_resume = AsyncMock()
    service.delete_resume = AsyncMock()
    service.resume_repository = mock_resume_repository
    return service


@pytest.fixture
def mock_latex_service():
    """Fixture for mocking LaTeX service."""
    service = AsyncMock(spec=LatexService)
    service.generate_resume_latex = AsyncMock()
    service.generate_cover_letter_latex = AsyncMock()
    service.compile_latex_to_pdf = AsyncMock()
    return service


@pytest.fixture
def mock_tex_service(mock_tex_header_repository, mock_preamble_repository):
    """Fixture for mocking Tex service."""
    service = AsyncMock(spec=LatexService)
    service.get_template = AsyncMock()
    service.format_template = AsyncMock()
    service.get_header = AsyncMock()
    service.format_header = AsyncMock()
    service.get_default_preamble = AsyncMock()
    service.get_preamble = AsyncMock()
    service.get_all_headers_by_category = AsyncMock()
    service.get_all_header_names_by_category = AsyncMock()
    service.clear_caches = AsyncMock()
    service.header_repository = mock_tex_header_repository
    service.preamble_repository = mock_preamble_repository
    return service


@pytest.fixture
def mock_llm_service(mock_profile_repository):
    """Fixture for mocking LLM service."""
    service = AsyncMock(spec=LLMService)
    service.generate_cover_letter = AsyncMock()
    service.get_completion = AsyncMock()
    service.configure_for_user = AsyncMock()
    service.profile_repository = mock_profile_repository
    return service


@pytest.fixture
def mock_prompt_service():
    """Fixture for mocking Prompt service."""
    service = AsyncMock(spec=PromptService)
    service.get_prompt = AsyncMock()
    service.get_system_prompt = AsyncMock()
    service.get_cover_letter_prompt = AsyncMock()
    service.get_portfolio_section_prompt = AsyncMock()
    return service


@pytest.fixture
def mock_resume_generation_service(
    mock_resume_repository,
    mock_profile_repository,
    mock_portfolio_repository,
    mock_llm_service,
    mock_tex_service,
):
    """Fixture for mocking ResumeGeneration service."""
    service = AsyncMock(spec=ResumeGenerationService)
    service.generate_resume_content = AsyncMock()
    service.generate_cover_letter = AsyncMock()
    service.llm = mock_llm_service
    service.tex = mock_tex_service
    service.resume_repository = mock_resume_repository
    service.profile_repository = mock_profile_repository
    service.portfolio_repository = mock_portfolio_repository
    return service


@pytest.fixture
def test_user():
    """Fixture for a test user."""
    return User(
        id="507f1f77bcf86cd799439011",
        email="test@example.com",
        username="Test User",
        hashed_password="hashed_password",
        is_active=True,
        is_verified=True,
    )


@pytest.fixture
def test_profile():
    """Fixture for a test profile."""
    return Profile(
        id="507f1f77bcf86cd799439022",
        user_id="507f1f77bcf86cd799439011",
        name="Test User",
        email="test@example.com",
        phone="+1234567890",
        location="Test City, TS",
        title="Software Engineer",
        summary="Experienced software developer with 5+ years of experience.",
        links={
            "linkedin": "https://linkedin.com/in/testuser",
            "github": "https://github.com/testuser",
        },
    )


@pytest.fixture
def test_portfolio():
    """Fixture for a test portfolio."""
    return Portfolio(
        id="507f1f77bcf86cd799439033",
        user_id="507f1f77bcf86cd799439011",
        name="Test Portfolio",
        work_experience=[
            {
                "company": "Test Company",
                "position": "Software Engineer",
                "start_date": "2018-01-01",
                "end_date": "2023-01-01",
                "description": "Developed web applications using Python",
                "technologies": ["Python", "FastAPI", "MongoDB"],
                "is_featured": True,
                "tags": ["backend", "web", "database"],
            }
        ],
        education=[
            {
                "institution": "Test University",
                "degree": "Bachelor of Science",
                "start_date": "2014-01-01",
                "end_date": "2018-01-01",
                "description": "Studied Computer Science",
                "is_featured": True,
                "tags": ["education", "degree"],
            }
        ],
        skills=[
            {"name": "Python", "level": 5, "category": "Programming"},
            {"name": "FastAPI", "level": 4, "category": "Framework"},
            {"name": "MongoDB", "level": 4, "category": "Database"},
        ],
    )


@pytest.fixture
def test_resume():
    """Fixture for a test resume."""
    return Resume(
        id="507f1f77bcf86cd799439044",
        user_id="507f1f77bcf86cd799439011",
        name="Test Resume",
        profile_id="507f1f77bcf86cd799439022",
        portfolio_id="507f1f77bcf86cd799439033",
        template_name="modern",
        sections=["summary", "work_experience", "education", "skills"],
        job_description="Software Developer position requiring Python experience",
        company_name="Tech Company Inc.",
        job_title="Senior Software Engineer",
        content={
            "summary": "Experienced software developer with 5+ years of experience.",
            "work_experience": "Work experience content...",
            "education": "Education content...",
            "skills": "Skills content...",
        },
    )


@pytest.fixture
def mock_get_current_user(test_user):
    """Mock the get_current_user dependency."""

    async def _get_current_user():
        return test_user

    return _get_current_user


@pytest.fixture
def app_with_mocked_dependencies(
    app,
    mock_user_repository,
    mock_profile_repository,
    mock_portfolio_repository,
    mock_resume_repository,
    mock_tex_header_repository,
    mock_preamble_repository,
    mock_get_current_user,
):
    """Create a FastAPI app with mocked dependencies."""
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repository
    app.dependency_overrides[get_profile_repository] = lambda: mock_profile_repository
    app.dependency_overrides[get_portfolio_repository] = (
        lambda: mock_portfolio_repository
    )
    app.dependency_overrides[get_resume_repository] = lambda: mock_resume_repository
    return app


@pytest.fixture
def client_with_mocked_dependencies(app_with_mocked_dependencies):
    """Create a test client with mocked dependencies."""
    return TestClient(app_with_mocked_dependencies)


@pytest.fixture
def auth_headers():
    """Fixture for authentication headers."""
    return {"Authorization": "Bearer test_token"}


@pytest.fixture(autouse=True)
def mock_env_vars():
    """Mock environment variables for testing."""
    with patch.dict(
        os.environ,
        {
            "MONGODB_URI": "mongodb://localhost:27017",
            "MONGODB_DB": "test_db",
            "JWT_SECRET_KEY": "test_secret_key",
            "JWT_ALGORITHM": "RS256",
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "15",
            "JWT_REFRESH_TOKEN_EXPIRE_DAYS": "7",
            "API_PREFIX": "/api",
            "DEBUG": "True",
            "ENVIRONMENT": "test",
            "LOG_LEVEL": "DEBUG",
        },
    ):
        yield
