"""Tests for API schemas."""

from datetime import datetime

import pytest
from beanie import PydanticObjectId
from pydantic import ValidationError

from api.schemas import (
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
    request = RegisterRequest(
        email="test@example.com",
        password="Password123!",
    )

    assert request.email == "test@example.com"
    assert request.password == "Password123!"


def test_register_request_invalid_email():
    with pytest.raises(ValidationError) as excinfo:
        RegisterRequest(
            email="invalid-email",
            password="Password123!",
        )

    errors = excinfo.value.errors()
    assert any(error["loc"] == ("email",) for error in errors)


def test_register_request_invalid_password():
    with pytest.raises(ValidationError) as excinfo:
        RegisterRequest(
            email="test@example.com",
            password="weak",
        )

    errors = excinfo.value.errors()
    assert any("password" in str(error["loc"]) for error in errors)


def test_login_request_valid():
    request = LoginRequest(
        email="test@example.com",
        password="Password123!",
    )

    assert request.email == "test@example.com"
    assert request.password == "Password123!"


def test_token_response_valid():
    response = TokenResponse(
        access_token="test_token",
        token_type="bearer",
    )

    assert response.access_token == "test_token"
    assert response.token_type == "bearer"


def test_resume_create_valid():
    request = ResumeCreate(
        job_description="Python backend engineer role at a startup.",
        compile_pdf=False,
    )

    assert "Python" in request.job_description
    assert request.compile_pdf is False


def test_resume_update_valid():
    request = ResumeUpdate(
        job_title="Software Engineer",
        company_name="Tech Company",
        job_description="A job description",
        content={"summary": "Experienced developer"},
    )

    assert request.job_title == "Software Engineer"
    assert request.company_name == "Tech Company"
    assert request.job_description == "A job description"
    assert request.content == {"summary": "Experienced developer"}


def test_resume_filter_valid():
    filter_params = ResumeFilter(
        title="Test",
        template_id="default",
        skip=10,
        limit=20,
    )

    assert filter_params.title == "Test"
    assert filter_params.template_id == "default"
    assert filter_params.skip == 10
    assert filter_params.limit == 20


def test_resume_response_valid():
    resume_id = PydanticObjectId()
    user_id = PydanticObjectId()
    profile_id = PydanticObjectId()
    portfolio_id = PydanticObjectId()

    response = ResumeResponse(
        id=resume_id,
        user_id=user_id,
        profile_id=profile_id,
        portfolio_id=portfolio_id,
        title="Test Resume",
        template_id="default",
        job_title="Software Engineer",
        company_name="Tech Company",
        job_description="Test job description",
        content={"summary": "Test summary"},
        created_at=datetime.fromisoformat("2023-01-01T00:00:00"),
        updated_at=datetime.fromisoformat("2023-01-02T00:00:00"),
    )

    assert str(response.id) == str(resume_id)
    assert response.title == "Test Resume"
    assert response.content == {"summary": "Test summary"}


def test_cover_letter_create_valid():
    resume_id = PydanticObjectId()
    request = CoverLetterCreate(resume_id=resume_id, generate_pdf=False)

    assert request.resume_id == resume_id
    assert request.generate_pdf is False


def test_cover_letter_response_valid():
    cover_letter_id = PydanticObjectId()
    user_id = PydanticObjectId()
    resume_id = PydanticObjectId()

    response = CoverLetterResponse(
        id=cover_letter_id,
        user_id=user_id,
        resume_id=resume_id,
        template_id="default",
        content="Dear hiring manager,",
        created_at=datetime.fromisoformat("2023-01-01T00:00:00"),
        updated_at=datetime.fromisoformat("2023-01-02T00:00:00"),
    )

    assert str(response.id) == str(cover_letter_id)
    assert response.content == "Dear hiring manager,"
