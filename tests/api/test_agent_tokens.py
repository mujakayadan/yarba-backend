"""Tests for agent access token auth and management."""

import jwt
import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from api.main import app as fastapi_app
from api.middleware.auth import get_current_active_user, get_current_user
from config.settings import settings
from core.models.agent_access_token import AgentAccessToken
from core.models.user import User
from core.utils.agent_access_token import generate_raw_token, hash_token


def _jwt_for_user(user: User) -> str:
    return jwt.encode(
        {"sub": user.email},
        settings.auth.jwt_secret_key.get_secret_value(),
        algorithm=settings.auth.jwt_algorithm,
    )


@pytest.mark.asyncio
async def test_create_and_use_agent_token(
    beanie_db, async_client: AsyncClient, test_user
):
    token = _jwt_for_user(test_user)
    create_resp = await async_client.post(
        "/api/v1/auth/agent-tokens",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "label": "test agent",
            "scopes": ["applications:read"],
            "expires_in_days": 30,
        },
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    body = create_resp.json()
    assert body["raw_token"].startswith("yarba_pat_")

    fastapi_app.dependency_overrides.pop(get_current_user, None)
    fastapi_app.dependency_overrides.pop(get_current_active_user, None)

    list_resp = await async_client.get(
        "/api/v1/applications",
        headers={"Authorization": f"Bearer {body['raw_token']}"},
    )
    assert list_resp.status_code == status.HTTP_200_OK
    assert list_resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_pat_cannot_create_pat(beanie_db, async_client: AsyncClient, test_user):
    raw = generate_raw_token()
    await AgentAccessToken(
        token_hash=hash_token(raw),
        user_id=test_user.id,
        label="existing",
        scopes=["applications:write"],
    ).insert()

    fastapi_app.dependency_overrides.pop(get_current_user, None)
    fastapi_app.dependency_overrides.pop(get_current_active_user, None)

    resp = await async_client.post(
        "/api/v1/auth/agent-tokens",
        headers={"Authorization": f"Bearer {raw}"},
        json={
            "label": "nested",
            "scopes": ["applications:write"],
        },
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_revoked_pat_rejected(beanie_db, test_user):
    raw = generate_raw_token()
    await AgentAccessToken(
        token_hash=hash_token(raw),
        user_id=test_user.id,
        label="revoked",
        scopes=["applications:read"],
        is_active=False,
    ).insert()

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/applications",
            headers={"Authorization": f"Bearer {raw}"},
        )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
