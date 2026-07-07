"""Tests for portfolio website chatbot API."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from api.dependencies.services import get_llm_service
from api.main import app as fastapi_app
from core.models.portfolio_website import PortfolioWebsite, WebsiteConfig
from core.services.llm_service import LLMService

CHAT_URL = "/api/v1/public/portfolio/chat"


@pytest.fixture
async def mock_chat_llm_service() -> AsyncMock:
    service = AsyncMock(spec=LLMService)
    service.get_chat_completion = AsyncMock(
        return_value={"llm_output": "I specialize in Python and FastAPI."}
    )
    return service


@pytest.fixture
async def published_chatbot_website(
    test_user,
    test_portfolio,
    beanie_db,
) -> PortfolioWebsite:
    website = PortfolioWebsite(
        user_id=test_user.id,
        portfolio_id=test_portfolio.id,
        subdomain="testuser",
        config=WebsiteConfig(chatbot_enabled=True),
        is_published=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await website.insert()
    return website


@pytest.fixture
async def chat_client(
    async_client: AsyncClient,
    mock_chat_llm_service: AsyncMock,
) -> AsyncClient:
    fastapi_app.dependency_overrides[get_llm_service] = lambda: mock_chat_llm_service
    yield async_client
    fastapi_app.dependency_overrides.pop(get_llm_service, None)


@pytest.mark.anyio
async def test_portfolio_chat_success(
    chat_client: AsyncClient,
    published_chatbot_website: PortfolioWebsite,
    test_profile,
    mock_chat_llm_service: AsyncMock,
):
    test_profile.life_story = "Built open-source tools for job seekers."
    await test_profile.save()

    response = await chat_client.post(
        CHAT_URL,
        json={
            "subdomain": published_chatbot_website.subdomain,
            "message": "What are your main skills?",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["response"] == "I specialize in Python and FastAPI."
    assert body["conversation_id"]

    mock_chat_llm_service.get_chat_completion.assert_awaited_once()
    call_kwargs = mock_chat_llm_service.get_chat_completion.await_args.kwargs
    messages = call_kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert "Built open-source tools for job seekers." in messages[0]["content"]
    assert messages[-1]["content"] == "What are your main skills?"


@pytest.mark.anyio
async def test_portfolio_chat_disabled(
    chat_client: AsyncClient,
    test_user,
    test_portfolio,
    beanie_db,
):
    website = PortfolioWebsite(
        user_id=test_user.id,
        portfolio_id=test_portfolio.id,
        subdomain="disabled-chat",
        config=WebsiteConfig(chatbot_enabled=False),
        is_published=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await website.insert()

    response = await chat_client.post(
        CHAT_URL,
        json={"subdomain": "disabled-chat", "message": "Hello"},
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_portfolio_chat_unknown_subdomain(chat_client: AsyncClient):
    response = await chat_client.post(
        CHAT_URL,
        json={"subdomain": "does-not-exist", "message": "Hello"},
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_portfolio_chat_unpublished_site(
    chat_client: AsyncClient,
    test_user,
    test_portfolio,
    beanie_db,
):
    website = PortfolioWebsite(
        user_id=test_user.id,
        portfolio_id=test_portfolio.id,
        subdomain="unpublished-chat",
        config=WebsiteConfig(chatbot_enabled=True),
        is_published=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await website.insert()

    response = await chat_client.post(
        CHAT_URL,
        json={"subdomain": "unpublished-chat", "message": "Hello"},
    )

    assert response.status_code == 404


@pytest.mark.anyio
async def test_portfolio_chat_invalid_subdomain(chat_client: AsyncClient):
    response = await chat_client.post(
        CHAT_URL,
        json={"subdomain": "bad--name", "message": "Hello"},
    )

    assert response.status_code == 400


@pytest.mark.anyio
async def test_portfolio_chat_includes_calendly_in_system_prompt(
    chat_client: AsyncClient,
    published_chatbot_website: PortfolioWebsite,
    test_profile,
    mock_chat_llm_service: AsyncMock,
):
    test_profile.personal_information.calendly_url = (
        "https://calendly.com/example-user/30min"
    )
    await test_profile.save()

    response = await chat_client.post(
        CHAT_URL,
        json={
            "subdomain": published_chatbot_website.subdomain,
            "message": "Can we schedule a call?",
        },
    )

    assert response.status_code == 200
    messages = mock_chat_llm_service.get_chat_completion.await_args.kwargs["messages"]
    system_prompt = messages[0]["content"]
    assert "https://calendly.com/example-user/30min" in system_prompt
    assert "Do not invent specific time slots" in system_prompt
