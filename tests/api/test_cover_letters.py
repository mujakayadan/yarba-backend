"""Tests for cover letter endpoints."""

import pytest
from fastapi import status
from httpx import AsyncClient

from ...core.models.resume import Resume
from ...core.models.user import User


@pytest.fixture
async def test_cover_letter(mock_current_user: User) -> Resume:
    """Create a test cover letter."""
    cover_letter = Resume(
        user=mock_current_user,
        title="Test Cover Letter",
        template_id="default",
        job_description="Test job description",
    )

    await cover_letter.insert()
    return cover_letter


@pytest.mark.asyncio
async def test_create_cover_letter(async_client: AsyncClient, auth_headers: dict):
    """Test creating a cover letter."""
    # Arrange
    cover_letter_data = {
        "title": "New Cover Letter",
        "template_id": "default",
    }

    # Act
    response = await async_client.post(
        "/api/v1/cover-letters",
        json=cover_letter_data,
        headers=auth_headers,
    )

    # Assert
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["title"] == cover_letter_data["title"]
    assert response.json()["template_id"] == cover_letter_data["template_id"]
    assert response.json()["is_cover_letter"] is True
    assert "id" in response.json()


@pytest.mark.asyncio
async def test_get_cover_letters(
    async_client: AsyncClient, auth_headers: dict, test_cover_letter: Resume
):
    """Test getting all cover letters."""
    # Act
    response = await async_client.get(
        "/api/v1/cover-letters",
        headers=auth_headers,
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1
    assert any(cl["id"] == str(test_cover_letter.id) for cl in response.json())


@pytest.mark.asyncio
async def test_get_cover_letter(
    async_client: AsyncClient, auth_headers: dict, test_cover_letter: Resume
):
    """Test getting a cover letter by ID."""
    # Act
    response = await async_client.get(
        f"/api/v1/cover-letters/{test_cover_letter.id}",
        headers=auth_headers,
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(test_cover_letter.id)
    assert response.json()["title"] == test_cover_letter.title
    assert response.json()["is_cover_letter"] is True


@pytest.mark.asyncio
async def test_get_cover_letter_not_found(
    async_client: AsyncClient, auth_headers: dict
):
    """Test getting a non-existent cover letter."""
    # Act
    response = await async_client.get(
        "/api/v1/cover-letters/nonexistent",
        headers=auth_headers,
    )

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_cover_letter(
    async_client: AsyncClient, auth_headers: dict, test_cover_letter: Resume
):
    """Test updating a cover letter."""
    # Arrange
    update_data = {
        "title": "Updated Cover Letter",
        "template_id": "modern",
    }

    # Act
    response = await async_client.put(
        f"/api/v1/cover-letters/{test_cover_letter.id}",
        json=update_data,
        headers=auth_headers,
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(test_cover_letter.id)
    assert response.json()["title"] == update_data["title"]
    assert response.json()["template_id"] == update_data["template_id"]
    assert response.json()["is_cover_letter"] is True


@pytest.mark.asyncio
async def test_update_cover_letter_not_found(
    async_client: AsyncClient, auth_headers: dict
):
    """Test updating a non-existent cover letter."""
    # Arrange
    update_data = {
        "title": "Updated Cover Letter",
        "template_id": "modern",
    }

    # Act
    response = await async_client.put(
        "/api/v1/cover-letters/nonexistent",
        json=update_data,
        headers=auth_headers,
    )

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_cover_letter(
    async_client: AsyncClient, auth_headers: dict, test_cover_letter: Resume
):
    """Test deleting a cover letter."""
    # Act
    response = await async_client.delete(
        f"/api/v1/cover-letters/{test_cover_letter.id}",
        headers=auth_headers,
    )

    # Assert
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify it's deleted
    get_response = await async_client.get(
        f"/api/v1/cover-letters/{test_cover_letter.id}",
        headers=auth_headers,
    )
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_cover_letter_not_found(
    async_client: AsyncClient, auth_headers: dict
):
    """Test deleting a non-existent cover letter."""
    # Act
    response = await async_client.delete(
        "/api/v1/cover-letters/nonexistent",
        headers=auth_headers,
    )

    # Assert
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_generate_cover_letter(
    async_client: AsyncClient, auth_headers: dict, test_cover_letter: Resume
):
    """Test generating cover letter content."""
    # Arrange
    generate_data = {
        "job_description": "Software Engineer job description",
    }

    # Act
    response = await async_client.post(
        f"/api/v1/cover-letters/{test_cover_letter.id}/generate",
        json=generate_data,
        headers=auth_headers,
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(test_cover_letter.id)
    assert "job_description" in response.json()
    assert "cover_letter_content" in response.json()


@pytest.mark.asyncio
async def test_get_cover_letter_pdf(
    async_client: AsyncClient, auth_headers: dict, test_cover_letter: Resume
):
    """Test getting a cover letter as PDF."""
    # Act
    response = await async_client.get(
        f"/api/v1/cover-letters/{test_cover_letter.id}/pdf",
        headers=auth_headers,
    )

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/octet-stream"
    assert len(response.content) > 0
