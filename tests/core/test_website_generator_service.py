"""Tests for website generator chatbot integration."""

import pytest

from core.models.portfolio_website import WebsiteConfig
from core.services.website_generator_service import WebsiteGeneratorService
from tests.factories import make_portfolio, make_profile, make_user


@pytest.mark.anyio
async def test_generator_includes_chatbot_assets_when_enabled(beanie_db):
    user = make_user()
    profile = make_profile(user_id=user.id)
    portfolio = make_portfolio(user_id=user.id, profile_id=profile.id)
    config = WebsiteConfig(
        chatbot_enabled=True, chatbot_welcome_message="Hello visitor!"
    )

    service = WebsiteGeneratorService()
    files = await service.generate_website(
        portfolio=portfolio,
        subdomain="janedoe",
        user=user,
        profile=profile,
        config=config,
    )

    assert "chatbot.css" in files
    assert "chatbot.js" in files
    assert "YARBA_CHAT" in files["index.html"]
    assert "chatbot.css" in files["index.html"]
    assert "Hello visitor!" in files["index.html"]


@pytest.mark.anyio
async def test_generator_omits_chatbot_assets_when_disabled(beanie_db):
    user = make_user()
    profile = make_profile(user_id=user.id)
    portfolio = make_portfolio(user_id=user.id, profile_id=profile.id)
    config = WebsiteConfig(chatbot_enabled=False)

    service = WebsiteGeneratorService()
    files = await service.generate_website(
        portfolio=portfolio,
        subdomain="janedoe",
        user=user,
        profile=profile,
        config=config,
    )

    assert "chatbot.css" not in files
    assert "chatbot.js" not in files
    assert "YARBA_CHAT" not in files["index.html"]
