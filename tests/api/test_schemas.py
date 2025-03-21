"""Tests for API schemas."""

import pytest
from pydantic import ValidationError

from ...api.schemas import (
    CoverLetterCreate,
    CoverLetterResponse,
    LoginRequest,
    RegisterRequest,
    ResumeCreate,
    ResumeFilter,
    ResumeResponse,
    ResumeUpdate,
    TokenResponse,
)


def test_register_request_valid():
    """Test valid RegisterRequest."""
    # Act
    request = RegisterRequest(
        email="test@example.com",
        password="Password123!",
        full_name="Test User",
    )

    # Assert
    assert request.email == "test@example.com"
    assert request.password == "Password123!"
    assert request.full_name == "Test User"


def test_register_request_invalid_email():
    """Test RegisterRequest with invalid email."""
    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        RegisterRequest(
            email="invalid-email",
            password="Password123!",
            full_name="Test User",
        )

    # Assert
    errors = excinfo.value.errors()
    assert any(error["loc"] == ("email",) for error in errors)


def test_register_request_invalid_password():
    """Test RegisterRequest with invalid password."""
    # Act & Assert
    with pytest.raises(ValidationError) as excinfo:
        RegisterRequest(
            email="test@example.com",
            password="weak",
            full_name="Test User",
        )

    # Assert
    errors = excinfo.value.errors()
    assert any(error["loc"] == ("password",) for error in errors)


def test_login_request_valid():
    """Test valid LoginRequest."""
    # Act
    request = LoginRequest(
        email="test@example.com",
        password="Password123!",
    )

    # Assert
    assert request.email == "test@example.com"
    assert request.password == "Password123!"


def test_token_response_valid():
    """Test valid TokenResponse."""
    # Act
    response = TokenResponse(
        access_token="test_token",
        token_type="bearer",
    )

    # Assert
    assert response.access_token == "test_token"
    assert response.token_type == "bearer"


def test_resume_create_valid():
    """Test valid ResumeCreate."""
    # Act
    request = ResumeCreate(
        title="Test Resume",
        template_id="default",
    )

    # Assert
    assert request.title == "Test Resume"
    assert request.template_id == "default"


def test_resume_update_valid():
    """Test valid ResumeUpdate."""
    # Act
    request = ResumeUpdate(
        title="Updated Resume",
        template_id="modern",
        job_title="Software Engineer",
        company_name="Tech Company",
        job_description="A job description",
        content={
            "personal_information": {"name": "Test User", "email": "test@example.com"}
        },
    )

    # Assert
    assert request.title == "Updated Resume"
    assert request.template_id == "modern"
    assert request.job_title == "Software Engineer"
    assert request.company_name == "Tech Company"
    assert request.job_description == "A job description"
    assert request.content == {
        "personal_information": {"name": "Test User", "email": "test@example.com"}
    }


def test_resume_filter_valid():
    """Test valid ResumeFilter."""
    # Act
    filter_params = ResumeFilter(
        title="Test",
        template_id="default",
        skip=10,
        limit=20,
        is_cover_letter=False,
    )

    # Assert
    assert filter_params.title == "Test"
    assert filter_params.template_id == "default"
    assert filter_params.skip == 10
    assert filter_params.limit == 20
    assert filter_params.is_cover_letter is False


def test_resume_response_valid():
    """Test valid ResumeResponse."""
    # Act
    from datetime import datetime

    response = ResumeResponse(
        id="123",
        user_id="user123",
        profile_id="profile123",
        portfolio_id="portfolio123",
        title="Test Resume",
        template_id="default",
        job_title="Software Engineer",
        company_name="Tech Company",
        job_description="Test job description",
        content={
            "personal_information": {"name": "Test User", "email": "test@example.com"},
            "skills": {"Technical": ["Python", "FastAPI"]},
            "work_experience": [
                {
                    "company": "Test Company",
                    "position": "Test Position",
                    "start_date": "2020-01-01",
                    "end_date": "2021-01-01",
                    "responsibilities": ["Test responsibility"],
                }
            ],
            "education": [
                {
                    "institution": "Test University",
                    "degree": "Test Degree",
                    "field_of_study": "Computer Science",
                    "start_date": "2016-01-01",
                    "end_date": "2020-01-01",
                }
            ],
        },
        created_at=datetime.fromisoformat("2023-01-01T00:00:00"),
        updated_at=datetime.fromisoformat("2023-01-02T00:00:00"),
        is_cover_letter=False,
    )

    # Assert
    assert response.id == "123"
    assert response.user_id == "user123"
    assert response.profile_id == "profile123"
    assert response.portfolio_id == "portfolio123"
    assert response.title == "Test Resume"
    assert response.template_id == "default"
    assert response.job_title == "Software Engineer"
    assert response.company_name == "Tech Company"
    assert response.job_description == "Test job description"
    assert "personal_information" in response.content
    assert "skills" in response.content
    assert "work_experience" in response.content
    assert "education" in response.content
    assert response.created_at.isoformat() == "2023-01-01T00:00:00"
    assert response.updated_at.isoformat() == "2023-01-02T00:00:00"
    assert response.is_cover_letter is False


def test_cover_letter_create_valid():
    """Test valid CoverLetterCreate."""
    # Act
    request = CoverLetterCreate(
        title="Test Cover Letter",
        template_id="default",
    )

    # Assert
    assert request.title == "Test Cover Letter"
    assert request.template_id == "default"


def test_cover_letter_response_valid():
    """Test valid CoverLetterResponse."""
    # Act
    from datetime import datetime

    response = CoverLetterResponse(
        id="123",
        user_id="user123",
        profile_id="profile123",
        portfolio_id="portfolio123",
        title="Test Cover Letter",
        template_id="default",
        job_title="Software Engineer",
        company_name="Tech Company",
        job_description="Test job description",
        content={"cover_letter": "This is a test cover letter content."},
        created_at=datetime.fromisoformat("2023-01-01T00:00:00"),
        updated_at=datetime.fromisoformat("2023-01-02T00:00:00"),
        is_cover_letter=True,
    )

    # Assert
    assert response.id == "123"
    assert response.user_id == "user123"
    assert response.profile_id == "profile123"
    assert response.portfolio_id == "portfolio123"
    assert response.title == "Test Cover Letter"
    assert response.template_id == "default"
    assert response.job_title == "Software Engineer"
    assert response.company_name == "Tech Company"
    assert response.job_description == "Test job description"
    assert response.content["cover_letter"] == "This is a test cover letter content."
    assert response.created_at.isoformat() == "2023-01-01T00:00:00"
    assert response.updated_at.isoformat() == "2023-01-02T00:00:00"
    assert response.is_cover_letter is True
