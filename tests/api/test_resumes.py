"""Tests for resume endpoints."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId
from fastapi import status
from httpx import AsyncClient

from core.models.resume import Resume


@pytest.mark.asyncio
async def test_create_resume(async_client: AsyncClient, auth_headers: dict):
    """Test creating a resume."""
    response = await async_client.post(
        "/api/v1/resumes",
        json={
            "job_description": "Senior Python developer role.",
            "compile_pdf": False,
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED, response.text
    body = response.json()
    assert body["job_description"] == "Senior Python developer role."
    assert "id" in body


@pytest.mark.asyncio
async def test_get_resumes(
    async_client: AsyncClient, auth_headers: dict, test_resume: Resume
):
    """Test getting paginated resumes."""
    response = await async_client.get(
        "/api/v1/resumes",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert "items" in body
    assert body["total"] >= 1
    assert any(item["id"] == str(test_resume.id) for item in body["items"])


@pytest.mark.asyncio
async def test_get_resume(
    async_client: AsyncClient, auth_headers: dict, test_resume: Resume
):
    """Test getting a resume by ID."""
    response = await async_client.get(
        f"/api/v1/resumes/{test_resume.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(test_resume.id)
    assert response.json()["title"] == test_resume.title


@pytest.mark.asyncio
async def test_get_resume_not_found(async_client: AsyncClient, auth_headers: dict):
    """Test getting a non-existent resume."""
    missing_id = PydanticObjectId()
    response = await async_client.get(
        f"/api/v1/resumes/{missing_id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_update_resume(
    async_client: AsyncClient, auth_headers: dict, test_resume: Resume
):
    """Test updating a resume."""
    response = await async_client.put(
        f"/api/v1/resumes/{test_resume.id}",
        json={
            "job_title": "Staff Engineer",
            "company_name": "Acme Corp",
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == str(test_resume.id)
    assert body["job_title"] == "Staff Engineer"
    assert body["company_name"] == "Acme Corp"
    assert body["title"] == test_resume.title


@pytest.mark.asyncio
async def test_update_resume_title_only(
    async_client: AsyncClient, auth_headers: dict, test_resume: Resume
):
    """Test updating only the resume title without changing company or job title."""
    new_title = "MBN Industrial Applied Ai Computer Vision Engineer"
    response = await async_client.put(
        f"/api/v1/resumes/{test_resume.id}",
        json={"title": new_title},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["title"] == new_title
    assert body["job_title"] == test_resume.job_title
    assert body["company_name"] == test_resume.company_name


@pytest.mark.asyncio
async def test_update_resume_not_found(async_client: AsyncClient, auth_headers: dict):
    """Test updating a non-existent resume."""
    missing_id = PydanticObjectId()
    response = await async_client.put(
        f"/api/v1/resumes/{missing_id}",
        json={"job_title": "Updated"},
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_resume(
    async_client: AsyncClient, auth_headers: dict, test_resume: Resume
):
    """Test deleting a resume."""
    response = await async_client.delete(
        f"/api/v1/resumes/{test_resume.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = await async_client.get(
        f"/api/v1/resumes/{test_resume.id}",
        headers=auth_headers,
    )
    assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_delete_resume_not_found(async_client: AsyncClient, auth_headers: dict):
    """Test deleting a non-existent resume."""
    missing_id = PydanticObjectId()
    response = await async_client.delete(
        f"/api/v1/resumes/{missing_id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_populate_resume_content(
    async_client: AsyncClient, auth_headers: dict, test_resume: Resume
):
    """Test populating resume textual content."""
    response = await async_client.post(
        f"/api/v1/resumes/{test_resume.id}/populate-text-content",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(test_resume.id)


@pytest.mark.asyncio
async def test_get_resume_pdf(
    async_client: AsyncClient,
    auth_headers: dict,
    test_resume: Resume,
    monkeypatch: pytest.MonkeyPatch,
):
    """Test resume PDF URL endpoint when PDF key already exists."""
    monkeypatch.setattr(
        "api.routers.resumes.get_storage_provider",
        lambda: MagicMock(
            get_url=MagicMock(return_value="https://example.com/resume.pdf")
        ),
    )
    test_resume.resume_pdf_key = "resumes/test.pdf"
    await test_resume.save()

    response = await async_client.get(
        f"/api/v1/resumes/{test_resume.id}/pdf",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["pdf_url"] == "https://example.com/resume.pdf"


@pytest.mark.asyncio
async def test_download_resume_pdf(
    async_client: AsyncClient,
    auth_headers: dict,
    test_resume: Resume,
    monkeypatch: pytest.MonkeyPatch,
):
    """Test resume PDF download endpoint streams bytes from storage."""
    pdf_bytes = b"%PDF-1.4 test resume"
    monkeypatch.setattr(
        "api.routers.resumes.get_storage_provider",
        lambda: MagicMock(
            get_file=AsyncMock(return_value=pdf_bytes),
        ),
    )
    test_resume.resume_pdf_key = "resumes/test.pdf"
    await test_resume.save()

    response = await async_client.get(
        f"/api/v1/resumes/{test_resume.id}/pdf/download",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.content == pdf_bytes
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
