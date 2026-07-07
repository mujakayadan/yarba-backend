"""Tests for cover letter endpoints."""

from unittest.mock import MagicMock

import pytest
from beanie import PydanticObjectId
from fastapi import status
from httpx import AsyncClient

from core.models.cover_letter import CoverLetter
from core.models.resume import Resume


@pytest.mark.asyncio
async def test_create_cover_letter(
    async_client: AsyncClient, auth_headers: dict, test_resume: Resume
):
    """Test creating a cover letter."""
    response = await async_client.post(
        "/api/v1/cover-letters",
        json={"resume_id": str(test_resume.id), "generate_pdf": False},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["resume_id"] == str(test_resume.id)
    assert "id" in body


@pytest.mark.asyncio
async def test_get_cover_letters(
    async_client: AsyncClient,
    auth_headers: dict,
    test_cover_letter: CoverLetter,
):
    """Test listing cover letters."""
    response = await async_client.get(
        "/api/v1/cover-letters",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    items = body["items"] if isinstance(body, dict) else body
    assert len(items) >= 1
    assert any(item["id"] == str(test_cover_letter.id) for item in items)


@pytest.mark.asyncio
async def test_get_cover_letter(
    async_client: AsyncClient,
    auth_headers: dict,
    test_cover_letter: CoverLetter,
):
    """Test getting a cover letter by ID."""
    response = await async_client.get(
        f"/api/v1/cover-letters/{test_cover_letter.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(test_cover_letter.id)


@pytest.mark.asyncio
async def test_get_cover_letter_not_found(
    async_client: AsyncClient, auth_headers: dict
):
    """Test getting a missing cover letter."""
    missing_id = PydanticObjectId()
    response = await async_client.get(
        f"/api/v1/cover-letters/{missing_id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_cover_letter(
    async_client: AsyncClient,
    auth_headers: dict,
    test_cover_letter: CoverLetter,
):
    """Test updating a cover letter."""
    response = await async_client.patch(
        f"/api/v1/cover-letters/{test_cover_letter.id}",
        json={"content": "Updated cover letter body"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["content"] == "Updated cover letter body"


@pytest.mark.asyncio
async def test_update_cover_letter_not_found(
    async_client: AsyncClient, auth_headers: dict
):
    """Test updating a missing cover letter."""
    missing_id = PydanticObjectId()
    response = await async_client.patch(
        f"/api/v1/cover-letters/{missing_id}",
        json={"content": "Updated"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_cover_letter(
    async_client: AsyncClient,
    auth_headers: dict,
    test_cover_letter: CoverLetter,
):
    """Test deleting a cover letter."""
    response = await async_client.delete(
        f"/api/v1/cover-letters/{test_cover_letter.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = await async_client.get(
        f"/api/v1/cover-letters/{test_cover_letter.id}",
        headers=auth_headers,
    )
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_cover_letter_not_found(
    async_client: AsyncClient, auth_headers: dict
):
    """Test deleting a missing cover letter."""
    missing_id = PydanticObjectId()
    response = await async_client.delete(
        f"/api/v1/cover-letters/{missing_id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_generate_cover_letter(
    async_client: AsyncClient,
    auth_headers: dict,
    test_cover_letter: CoverLetter,
):
    """Test generating cover letter content."""
    response = await async_client.post(
        f"/api/v1/cover-letters/{test_cover_letter.id}/generate",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(test_cover_letter.id)


@pytest.mark.asyncio
async def test_get_cover_letter_pdf(
    async_client: AsyncClient,
    auth_headers: dict,
    test_cover_letter: CoverLetter,
    monkeypatch: pytest.MonkeyPatch,
):
    """Test PDF URL endpoint when PDF already exists in storage."""
    monkeypatch.setattr(
        "api.routers.cover_letters.get_storage_provider",
        lambda: MagicMock(
            get_url=MagicMock(return_value="https://example.com/cover.pdf")
        ),
    )
    test_cover_letter.cover_letter_pdf_key = "cover-letters/test.pdf"
    await test_cover_letter.save()

    response = await async_client.get(
        f"/api/v1/cover-letters/{test_cover_letter.id}/pdf",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert "pdf_url" in response.json()
