"""Tests for the remaining session user endpoints."""

import pytest
from fastapi import status
from httpx import AsyncClient

from core.models.user import User


@pytest.mark.asyncio
async def test_get_current_user(async_client: AsyncClient, test_user: User) -> None:
    response = await async_client.get("/api/v1/auth/me")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["email"] == test_user.email
    assert body["username"] == test_user.username
    assert body["auth_provider"] == "password"
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_update_setup_progress(
    async_client: AsyncClient, test_user: User
) -> None:
    response = await async_client.put(
        "/api/v1/auth/users/me/setup-progress",
        json={"setup_completed": True},
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["email"] == test_user.email
    assert body["is_new_user"] is False
    assert body["current_setup_step"] == 0
    stored = await User.get(test_user.id)
    assert stored is not None
    assert stored.is_new_user is False
    assert stored.current_setup_step == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/verify-email",
        "/api/v1/auth/change-password",
    ],
)
async def test_removed_auth_routes_are_absent(
    async_client: AsyncClient, path: str
) -> None:
    response = await async_client.post(path, json={})
    assert response.status_code == status.HTTP_404_NOT_FOUND
