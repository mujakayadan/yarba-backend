"""Tests for API dependencies."""

import pytest
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from ...api.middleware.auth import get_current_user, verify_token
from ...core.models.user import User


def test_verify_token_missing_token():
    """Test verify_token with missing token."""
    # Create a test app with the verify_token dependency
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint(token: str = Depends(verify_token)):
        return {"token": token}

    # Create a test client
    client = TestClient(app)

    # Act
    response = client.get("/test")

    # Assert
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Not authenticated" in response.json()["detail"]


def test_verify_token_invalid_token():
    """Test verify_token with invalid token."""
    # Create a test app with the verify_token dependency
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint(token: str = Depends(verify_token)):
        return {"token": token}

    # Create a test client
    client = TestClient(app)

    # Act
    response = client.get("/test", headers={"Authorization": "Bearer invalid_token"})

    # Assert
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Could not validate credentials" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_current_user_not_found():
    """Test get_current_user with user not found."""
    # Mock token and user repository
    token = "valid_token"

    class MockUserRepo:
        async def find_one(self, query):
            return None

    # Act & Assert
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user(token, MockUserRepo())

    # Assert
    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Could not validate credentials" in excinfo.value.detail


@pytest.mark.asyncio
async def test_get_current_user_success():
    """Test get_current_user with valid token and user."""
    # Mock token and user repository
    token = "valid_token"
    mock_user = User(
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashed_password",
    )

    class MockUserRepo:
        async def find_one(self, query):
            return mock_user

    # Override JWT decode function
    from ...api.middleware.auth import jwt

    original_decode = jwt.decode

    def mock_decode(*args, **kwargs):
        return {"sub": "test@example.com"}

    jwt.decode = mock_decode

    try:
        # Act
        user = await get_current_user(token, MockUserRepo())

        # Assert
        assert user == mock_user
        assert user.email == "test@example.com"
    finally:
        # Restore original function
        jwt.decode = original_decode
