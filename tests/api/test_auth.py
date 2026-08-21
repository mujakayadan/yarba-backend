"""Tests for authentication endpoints."""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, status
from httpx import AsyncClient

from api.main import app as fastapi_app
from core.database.factory import get_auth_service

LEGAL_ACCEPTANCE = {
    "terms_version": "2026-08-19",
    "acceptable_use_version": "2026-08-19",
    "privacy_version": "2026-08-19",
    "ai_data_use_version": "2026-08-19",
    "terms_accepted": True,
    "acceptable_use_accepted": True,
    "privacy_acknowledged": True,
    "ai_data_use_acknowledged": True,
    "minimum_age_confirmed": True,
    "acceptance_surface": "firebase_registration",
}


@pytest.mark.asyncio
async def test_register_success(async_client_auth: AsyncClient):
    """Test successful user registration."""
    response = await async_client_auth.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "Password123!",
            "legal_acceptance": LEGAL_ACCEPTANCE,
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["access_token"] == "test-access-token"
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "newuser@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(
    async_client_auth: AsyncClient, mock_auth_service, registered_user
):
    """Test registration with duplicate email."""
    from core.auth.error_codes import EMAIL_ALREADY_REGISTERED
    from core.exceptions.base import ConflictException

    mock_auth_service.register_with_firebase = AsyncMock(
        side_effect=ConflictException(
            message="An account with this email already exists. Please sign in.",
            error_code=EMAIL_ALREADY_REGISTERED,
        )
    )

    response = await async_client_auth.post(
        "/api/v1/auth/register",
        json={
            "email": registered_user["email"],
            "password": "Password123!",
            "legal_acceptance": LEGAL_ACCEPTANCE,
        },
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    body = response.json()
    assert body["status"] == "error"
    assert body["error_code"] == EMAIL_ALREADY_REGISTERED
    assert "already exists" in body["message"]


@pytest.mark.asyncio
async def test_register_invalid_email(async_client: AsyncClient):
    """Test registration with invalid email format."""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "invalid-email", "password": "Password123!"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "email" in response.json()["detail"][0]["loc"]


@pytest.mark.asyncio
async def test_register_weak_password(async_client: AsyncClient):
    """Test registration with weak password."""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "weakpass@example.com", "password": "weak"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "password" in str(response.json()["detail"]).lower()


@pytest.mark.asyncio
async def test_login_success(async_client_auth: AsyncClient):
    """Test successful Firebase token login."""
    response = await async_client_auth.post(
        "/api/v1/auth/login",
        json={"id_token": "valid-firebase-id-token"},
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["access_token"] == "test-access-token"
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_token(async_client_auth: AsyncClient, mock_auth_service):
    """Test login with invalid Firebase token."""
    mock_auth_service.login_with_firebase = AsyncMock(
        side_effect=HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )
    )
    fastapi_app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

    response = await async_client_auth.post(
        "/api/v1/auth/login",
        json={"id_token": "invalid-token"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_login_missing_token(async_client: AsyncClient):
    """Test login without id_token."""
    response = await async_client.post("/api/v1/auth/login", json={})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
