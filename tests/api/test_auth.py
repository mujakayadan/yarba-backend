"""Tests for authentication endpoints."""

import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(async_client: AsyncClient):
    """Test successful user registration."""
    # Arrange
    user_data = {
        "email": "newuser@example.com",
        "password": "Password123!",
        "full_name": "New User",
    }

    # Act
    response = await async_client.post("/api/v1/auth/register", json=user_data)

    # Assert
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == {"message": "User registered successfully"}


@pytest.mark.asyncio
async def test_register_duplicate_email(async_client: AsyncClient, registered_user):
    """Test registration with duplicate email."""
    # Arrange
    user_data = {
        "email": registered_user["email"],  # Use the same email as registered_user
        "password": "Password123!",
        "full_name": "Duplicate User",
    }

    # Act
    response = await async_client.post("/api/v1/auth/register", json=user_data)

    # Assert
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Email already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_invalid_email(async_client: AsyncClient):
    """Test registration with invalid email format."""
    # Arrange
    user_data = {
        "email": "invalid-email",
        "password": "Password123!",
        "full_name": "Invalid Email User",
    }

    # Act
    response = await async_client.post("/api/v1/auth/register", json=user_data)

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "email" in response.json()["detail"][0]["loc"]


@pytest.mark.asyncio
async def test_register_weak_password(async_client: AsyncClient):
    """Test registration with weak password."""
    # Arrange
    user_data = {
        "email": "weakpass@example.com",
        "password": "weak",
        "full_name": "Weak Password User",
    }

    # Act
    response = await async_client.post("/api/v1/auth/register", json=user_data)

    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "password" in response.json()["detail"][0]["loc"]


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient, registered_user):
    """Test successful login."""
    # Arrange
    login_data = {
        "username": registered_user["email"],
        "password": registered_user["password"],
    }

    # Act
    response = await async_client.post("/api/v1/auth/login", data=login_data)

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_email(async_client: AsyncClient):
    """Test login with invalid email."""
    # Arrange
    login_data = {
        "username": "nonexistent@example.com",
        "password": "Password123!",
    }

    # Act
    response = await async_client.post("/api/v1/auth/login", data=login_data)

    # Assert
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Incorrect email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_wrong_password(async_client: AsyncClient, registered_user):
    """Test login with wrong password."""
    # Arrange
    login_data = {
        "username": registered_user["email"],
        "password": "WrongPassword123!",
    }

    # Act
    response = await async_client.post("/api/v1/auth/login", data=login_data)

    # Assert
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Incorrect email or password" in response.json()["detail"]
