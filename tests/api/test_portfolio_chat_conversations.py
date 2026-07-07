"""Tests for stored portfolio chat conversations."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from api.dependencies.services import get_llm_service
from api.main import app as fastapi_app
from core.models.portfolio_chat_conversation import PortfolioChatConversation
from core.models.portfolio_website import PortfolioWebsite, WebsiteConfig
from core.services.llm_service import LLMService

CHAT_URL = "/api/v1/public/portfolio/chat"
LIST_URL = "/api/v1/portfolio-websites/chat/conversations"


@pytest.fixture
async def mock_chat_llm_service() -> AsyncMock:
    service = AsyncMock(spec=LLMService)
    service.get_chat_completion = AsyncMock(
        return_value={"llm_output": "I built several FastAPI services."}
    )
    return service


@pytest.fixture
async def published_chatbot_website_with_storage(
    test_user,
    test_portfolio,
    beanie_db,
) -> PortfolioWebsite:
    website = PortfolioWebsite(
        user_id=test_user.id,
        portfolio_id=test_portfolio.id,
        subdomain="stored-chat",
        config=WebsiteConfig(
            chatbot_enabled=True,
            chatbot_store_conversations=True,
        ),
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
async def test_chat_persists_conversation_when_storage_enabled(
    chat_client: AsyncClient,
    published_chatbot_website_with_storage: PortfolioWebsite,
):
    response = await chat_client.post(
        CHAT_URL,
        json={
            "subdomain": published_chatbot_website_with_storage.subdomain,
            "message": "Tell me about your backend work",
        },
        headers={
            "User-Agent": "TestBrowser/1.0",
            "Referer": "https://example.com/",
        },
    )

    assert response.status_code == 200
    body = response.json()
    conversation_id = body["conversation_id"]

    stored = await PortfolioChatConversation.find_one(
        PortfolioChatConversation.conversation_id == conversation_id
    )
    assert stored is not None
    assert stored.preview == "Tell me about your backend work"
    assert stored.message_count == 2
    assert stored.messages[-1].content == "I built several FastAPI services."
    assert stored.metadata.user_agent == "TestBrowser/1.0"
    assert stored.metadata.referrer == "https://example.com/"


@pytest.mark.anyio
async def test_chat_uses_server_history_when_storage_enabled(
    chat_client: AsyncClient,
    published_chatbot_website_with_storage: PortfolioWebsite,
    mock_chat_llm_service: AsyncMock,
):
    first = await chat_client.post(
        CHAT_URL,
        json={
            "subdomain": published_chatbot_website_with_storage.subdomain,
            "message": "First question",
        },
    )
    conversation_id = first.json()["conversation_id"]

    await chat_client.post(
        CHAT_URL,
        json={
            "subdomain": published_chatbot_website_with_storage.subdomain,
            "message": "Second question",
            "conversation_id": conversation_id,
            "history": [],
        },
    )

    second_call = mock_chat_llm_service.get_chat_completion.await_args_list[1].kwargs
    messages = second_call["messages"]
    user_messages = [item["content"] for item in messages if item["role"] == "user"]
    assert user_messages == ["First question", "Second question"]


@pytest.mark.anyio
async def test_chat_does_not_persist_when_storage_disabled(
    chat_client: AsyncClient,
    test_user,
    test_portfolio,
    beanie_db,
):
    website = PortfolioWebsite(
        user_id=test_user.id,
        portfolio_id=test_portfolio.id,
        subdomain="no-storage-chat",
        config=WebsiteConfig(chatbot_enabled=True, chatbot_store_conversations=False),
        is_published=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await website.insert()

    response = await chat_client.post(
        CHAT_URL,
        json={"subdomain": website.subdomain, "message": "Hello"},
    )

    assert response.status_code == 200
    count = await PortfolioChatConversation.find_all().count()
    assert count == 0


@pytest.mark.anyio
async def test_list_chat_conversations_authenticated(
    chat_client: AsyncClient,
    published_chatbot_website_with_storage: PortfolioWebsite,
):
    chat_response = await chat_client.post(
        CHAT_URL,
        json={
            "subdomain": published_chatbot_website_with_storage.subdomain,
            "message": "Are you open to contract work?",
        },
    )
    assert chat_response.status_code == 200

    response = await chat_client.get(LIST_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["stats"]["total_conversations"] == 1
    assert body["stats"]["total_messages"] == 2
    assert body["conversations"][0]["preview"] == "Are you open to contract work?"


@pytest.mark.anyio
async def test_get_chat_conversation_detail(
    chat_client: AsyncClient,
    published_chatbot_website_with_storage: PortfolioWebsite,
):
    chat_response = await chat_client.post(
        CHAT_URL,
        json={
            "subdomain": published_chatbot_website_with_storage.subdomain,
            "message": "What stack do you use?",
        },
    )
    assert chat_response.status_code == 200
    conversation_id = chat_response.json()["conversation_id"]

    response = await chat_client.get(f"{LIST_URL}/{conversation_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["conversation_id"] == conversation_id
    assert len(body["messages"]) == 2
    assert body["messages"][0]["role"] == "user"
