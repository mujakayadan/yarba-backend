"""Tests for resume endpoints."""

import pytest
from fastapi import status
from httpx import AsyncClient

from ...core.models.resume import Resume
from ...core.models.user import User


@pytest.fixture
async def test_resume(mock_current_user: User) -> Resume:
    """Create a test resume."""
    resume = Resume(
        user=mock_current_user,
        title="Test Resume",
        template_id="default",
        job_description="Test job description",
        personal_information={"name": "Test User", "email": "test@example.com"},
        career_summary="Test career summary",
        skills={"Technical": ["Python", "FastAPI"]},
        work_experience=[
            {
                "company": "Test Company",
                "position": "Test Position",
                "start_date": "2020-01-01",
                "end_date": "2021-01-01",
                "responsibilities": ["Test responsibility"],
            }
        ],
        education=[
            {
                "institution": "Test University",
                "degree": "Test Degree",
                "field_of_study": "Computer Science",
                "start_date": "2016-01-01",
                "end_date": "2020-01-01",
            }
        ],
    )

    await resume.insert()
    return resume


@pytest.mark.asyncio
async def test_create_resume(async_client: AsyncClient, auth_headers: dict):
    """Test creating a resume."""
    # Arrange
    resume_data = {
        "title": "New Resume",
        "template_id": "default",
    }

    # Act
    response = await async_client.post(
        "/api/v1/resumes",
        json=resume_data,
        headers=auth_headers,
    )

    # Assert
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["title"] == resume_data["title"]
    assert response.json()["template_id"] == resume_data["template_id"]
    assert "id" in response.json()


@pytest.mark.asyncio
async def test_get_resumes(
    async_client: AsyncClient, auth_headers: dict, test_resume: Resume
):
    """Test getting all resumes."""
    # Act
    response = await async_client.get(
        "/api/v1/resumes",
        headers=auth_headers,
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1
    assert any(resume["id"] == str(test_resume.id) for resume in response.json())


@pytest.mark.asyncio
async def test_get_resume(
    async_client: AsyncClient, auth_headers: dict, test_resume: Resume
):
    """Test getting a resume by ID."""
    # Act
    response = await async_client.get(
        f"/api/v1/resumes/{test_resume.id}",
        headers=auth_headers,
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(test_resume.id)
    assert response.json()["title"] == test_resume.title


@pytest.mark.asyncio
async def test_get_resume_not_found(async_client: AsyncClient, auth_headers: dict):
    """Test getting a non-existent resume."""
    # Act
    response = await async_client.get(
        "/api/v1/resumes/nonexistent",
        headers=auth_headers,
    )

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_resume(
    async_client: AsyncClient, auth_headers: dict, test_resume: Resume
):
    """Test updating a resume."""
    # Arrange
    update_data = {
        "title": "Updated Resume",
        "template_id": "modern",
    }

    # Act
    response = await async_client.put(
        f"/api/v1/resumes/{test_resume.id}",
        json=update_data,
        headers=auth_headers,
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(test_resume.id)
    assert response.json()["title"] == update_data["title"]
    assert response.json()["template_id"] == update_data["template_id"]


@pytest.mark.asyncio
async def test_update_resume_not_found(async_client: AsyncClient, auth_headers: dict):
    """Test updating a non-existent resume."""
    # Arrange
    update_data = {
        "title": "Updated Resume",
        "template_id": "modern",
    }

    # Act
    response = await async_client.put(
        "/api/v1/resumes/nonexistent",
        json=update_data,
        headers=auth_headers,
    )

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_resume(
    async_client: AsyncClient, auth_headers: dict, test_resume: Resume
):
    """Test deleting a resume."""
    # Act
    response = await async_client.delete(
        f"/api/v1/resumes/{test_resume.id}",
        headers=auth_headers,
    )

    # Assert
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify it's deleted
    get_response = await async_client.get(
        f"/api/v1/resumes/{test_resume.id}",
        headers=auth_headers,
    )
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_resume_not_found(async_client: AsyncClient, auth_headers: dict):
    """Test deleting a non-existent resume."""
    # Act
    response = await async_client.delete(
        "/api/v1/resumes/nonexistent",
        headers=auth_headers,
    )

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_generate_resume(
    async_client: AsyncClient, auth_headers: dict, test_resume: Resume
):
    """Test generating resume content."""
    # Arrange
    generate_data = {
        "job_description": "Software Engineer job description",
        "selected_sections": {
            "personal_information": "hardcode",
            "career_summary": "ai",
            "skills": "hardcode",
            "work_experience": "hardcode",
            "education": "hardcode",
        },
    }

    # Act
    response = await async_client.post(
        f"/api/v1/resumes/{test_resume.id}/generate",
        json=generate_data,
        headers=auth_headers,
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(test_resume.id)
    assert "job_description" in response.json()


@pytest.mark.asyncio
async def test_get_resume_pdf(
    async_client: AsyncClient, auth_headers: dict, test_resume: Resume
):
    """Test getting a resume as PDF."""
    # Act
    response = await async_client.get(
        f"/api/v1/resumes/{test_resume.id}/pdf",
        headers=auth_headers,
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/octet-stream"
    assert len(response.content) > 0
