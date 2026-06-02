"""Tests for API dependencies."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from jose import JWTError

from api.middleware.auth import get_current_user, verify_token
from tests.factories import make_user


def test_verify_token_missing_token():
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint(payload: dict = Depends(verify_token)):
        return payload

    client = TestClient(app)
    response = client.get("/test")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Authentication credentials not provided" in response.json()["detail"]


def test_verify_token_invalid_token():
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint(payload: dict = Depends(verify_token)):
        return payload

    client = TestClient(app)

    with (
        patch("api.middleware.auth.jwt.decode", side_effect=JWTError("invalid jwt")),
        patch(
            "api.middleware.auth.FirebaseAuth.verify_token",
            new_callable=AsyncMock,
            side_effect=Exception("invalid firebase"),
        ),
    ):
        response = client.get(
            "/test",
            headers={"Authorization": "Bearer invalid_token"},
        )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid authentication token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_current_user_not_found():
    token_payload = {"token_type": "jwt", "sub": "missing@example.com"}

    class MockUserRepo:
        async def get_by_email(self, _email):
            return None

    with pytest.raises(HTTPException) as excinfo:
        await get_current_user(token_payload, MockUserRepo())

    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "User not found" in excinfo.value.detail


@pytest.mark.asyncio
async def test_get_current_user_success():
    token_payload = {"token_type": "jwt", "sub": "test@example.com"}
    mock_user = make_user()

    class MockUserRepo:
        async def get_by_email(self, _email):
            return mock_user

    user = await get_current_user(token_payload, MockUserRepo())

    assert user == mock_user
    assert user.email == "test@example.com"
