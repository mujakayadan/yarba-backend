"""Tests for health check endpoint."""

import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient):
    """Test health check endpoint."""
    # Act
    response = await async_client.get("/")

    # Assert
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "ok"
    assert "version" in response.json()
