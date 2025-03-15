"""Test configuration for pytest."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import motor.motor_asyncio
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ..api.dependencies import (
    get_current_user,
    get_resume_repository,
    get_user_repository,
)
from ..core.database.repositories.resume import ResumeRepository
from ..core.database.repositories.user import UserRepository
from ..core.services.auth import AuthService
from ..core.services.resume import ResumeService
from ..main import create_app


@pytest.fixture
def app():
    """Create a FastAPI app for testing."""
    return create_app()


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

    db.resumes = AsyncMock()
    db.resumes.find_one = AsyncMock()
    db.resumes.insert_one = AsyncMock()
    db.resumes.update_one = AsyncMock()
    db.resumes.delete_one = AsyncMock()
    db.resumes.find = AsyncMock()

    return db


@pytest.fixture
def mock_user_repository():
    """Fixture for mocking user repository."""
    repository = AsyncMock(spec=UserRepository)
    repository.find_by_email = AsyncMock()
    repository.create = AsyncMock()
    repository.find_by_id = AsyncMock()
    repository.update = AsyncMock()
    repository.delete = AsyncMock()
    return repository


@pytest.fixture
def mock_resume_repository():
    """Fixture for mocking resume repository."""
    repository = AsyncMock(spec=ResumeRepository)
    repository.find_by_id = AsyncMock()
    repository.find_all = AsyncMock()
    repository.create = AsyncMock()
    repository.update = AsyncMock()
    repository.delete = AsyncMock()
    return repository


@pytest.fixture
def mock_auth_service(mock_user_repository):
    """Fixture for mocking auth service."""
    service = AsyncMock(spec=AuthService)
    service.register_user = AsyncMock()
    service.login_user = AsyncMock()
    service.user_repository = mock_user_repository
    return service


@pytest.fixture
def mock_resume_service(mock_resume_repository, mock_user_repository):
    """Fixture for mocking resume service."""
    service = AsyncMock(spec=ResumeService)
    service.create_resume = AsyncMock()
    service.get_resume_by_id = AsyncMock()
    service.get_resumes = AsyncMock()
    service.update_resume = AsyncMock()
    service.delete_resume = AsyncMock()
    service.resume_repository = mock_resume_repository
    service.user_repository = mock_user_repository
    return service


@pytest.fixture
def test_user():
    """Fixture for a test user."""
    return {
        "id": "507f1f77bcf86cd799439011",
        "email": "test@example.com",
        "full_name": "Test User",
        "hashed_password": "hashed_password",
    }


@pytest.fixture
def test_resume():
    """Fixture for a test resume."""
    return {
        "id": "507f1f77bcf86cd799439022",
        "title": "Test Resume",
        "user_id": "507f1f77bcf86cd799439011",
        "template_id": "default",
        "job_description": "Software Developer",
        "personal_information": {
            "name": "Test User",
            "email": "test@example.com",
            "phone": "123-456-7890",
            "address": "123 Test St, Test City, TS 12345",
        },
        "career_summary": "Experienced software developer with 5 years of experience.",
        "skills": {
            "Technical": ["Python", "FastAPI", "MongoDB"],
            "Soft": ["Communication", "Teamwork"],
        },
        "work_experience": [
            {
                "company": "Test Company",
                "position": "Software Developer",
                "start_date": "2018-01-01",
                "end_date": "2023-01-01",
                "responsibilities": [
                    "Developed web applications using Python and FastAPI",
                    "Worked with MongoDB for data storage",
                ],
            }
        ],
        "education": [
            {
                "institution": "Test University",
                "degree": "Bachelor of Science",
                "field_of_study": "Computer Science",
                "start_date": "2014-01-01",
                "end_date": "2018-01-01",
            }
        ],
        "created_at": "2023-01-01T00:00:00",
        "updated_at": "2023-01-02T00:00:00",
        "is_cover_letter": False,
    }


@pytest.fixture
def test_cover_letter():
    """Fixture for a test cover letter."""
    return {
        "id": "507f1f77bcf86cd799439033",
        "title": "Test Cover Letter",
        "user_id": "507f1f77bcf86cd799439011",
        "template_id": "default",
        "job_description": "Software Developer",
        "cover_letter_content": "This is a test cover letter content.",
        "created_at": "2023-01-01T00:00:00",
        "updated_at": "2023-01-02T00:00:00",
        "is_cover_letter": True,
    }


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
    mock_resume_repository,
    mock_get_current_user,
):
    """Create a FastAPI app with mocked dependencies."""
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repository
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
            "JWT_ALGORITHM": "HS256",
            "JWT_EXPIRATION_MINUTES": "15",
            "API_PREFIX": "/api",
            "DEBUG": "True",
            "ENVIRONMENT": "test",
            "LOG_LEVEL": "DEBUG",
        },
    ):
        yield
