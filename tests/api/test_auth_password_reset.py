"""Tests for password reset email flow."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from api.main import app as fastapi_app
from core.auth.firebase import FirebaseAuth
from core.database.factory import get_auth_service
from core.services.auth_service import AuthService
from core.services.email_clients.resend_client import ResendClient


@pytest.mark.asyncio
async def test_send_password_reset_email_uses_firebase_and_resend():
    resend_client = AsyncMock(spec=ResendClient)
    service = AuthService(resend_client=resend_client)

    with patch.object(
        FirebaseAuth,
        "generate_password_reset_link",
        new=AsyncMock(return_value="https://example.com/reset"),
    ) as mock_generate:
        await service.send_password_reset_email("user@example.com")

    mock_generate.assert_awaited_once_with("user@example.com")
    resend_client.send_email.assert_awaited_once()
    call_kwargs = resend_client.send_email.await_args.kwargs
    assert call_kwargs["to"] == "user@example.com"
    assert "https://example.com/reset" in call_kwargs["text"]
    assert "no changes have been made" in call_kwargs["text"]
    assert "Reset your password" in call_kwargs["html"]
    assert "background:#3F72AF" in call_kwargs["html"]


@pytest.mark.asyncio
async def test_forgot_password_endpoint(
    async_client_auth: AsyncClient, mock_auth_service
):
    mock_auth_service.send_password_reset_email = AsyncMock(return_value=True)
    fastapi_app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

    response = await async_client_auth.post(
        "/api/v1/auth/forgot-password",
        json={"email": "user@example.com"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert "Password reset instructions sent" in response.json()["message"]
    mock_auth_service.send_password_reset_email.assert_awaited_once_with(
        "user@example.com"
    )
