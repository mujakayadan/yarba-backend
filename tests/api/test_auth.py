"""Tests for authentication endpoints."""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, status
from httpx import AsyncClient

from api.main import app as fastapi_app
from core.database.factory import get_auth_service


@pytest.mark.asyncio
async def test_register_success(async_client_auth: AsyncClient):
    """Test successful user registration."""
    response = await async_client_auth.post(
        "/api/v1/auth/register",
        json={"email": "newuser@example.com", "password": "Password123!"},
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
    mock_auth_service.register_with_firebase = AsyncMock(
        side_effect=HTTPException(status_code=400, detail="Email already registered")
    )

    response = await async_client_auth.post(
        "/api/v1/auth/register",
        json={
            "email": registered_user["email"],
            "password": "Password123!",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Email already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_invalid_email(async_client: AsyncClient):
    """Test registration with invalid email format."""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "invalid-email", "password": "Password123!"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "email" in response.json()["detail"][0]["loc"]


@pytest.mark.asyncio
async def test_register_weak_password(async_client: AsyncClient):
    """Test registration with weak password."""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "weakpass@example.com", "password": "weak"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
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

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
