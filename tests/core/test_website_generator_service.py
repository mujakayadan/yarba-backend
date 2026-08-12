"""Tests for website generator chatbot integration."""

from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image

from core.models.portfolio import WorkExperience
from core.models.portfolio_website import WebsiteConfig
from core.services.website_generator_service import WebsiteGeneratorService
from tests.factories import make_portfolio, make_profile, make_user


def _make_test_profile_picture() -> bytes:
    image = Image.new("RGB", (120, 80), color=(30, 120, 220))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


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


@pytest.mark.anyio
async def test_generator_orders_work_experience_newest_first(beanie_db):
    user = make_user()
    profile = make_profile(user_id=user.id)
    portfolio = make_portfolio(
        user_id=user.id,
        profile_id=profile.id,
        work_experience=[
            WorkExperience(job_title="Older role", time="03/2024 - 03/2025"),
            WorkExperience(job_title="Newest role", time="08/25 - 08/26"),
        ],
    )

    service = WebsiteGeneratorService()
    files = await service.generate_website(
        portfolio=portfolio,
        subdomain="janedoe",
        user=user,
        profile=profile,
        config=WebsiteConfig(theme="modern"),
    )

    html = files["index.html"]
    assert html.index("Newest role") < html.index("Older role")


@pytest.mark.anyio
async def test_generator_builds_favicon_from_profile_picture(beanie_db):
    user = make_user()
    profile = make_profile(
        user_id=user.id,
        profile_picture_key="profile_pictures/test-user.png",
    )
    portfolio = make_portfolio(user_id=user.id, profile_id=profile.id)
    config = WebsiteConfig(theme="threejs")

    mock_storage = AsyncMock()
    mock_storage.get_file.return_value = _make_test_profile_picture()

    service = WebsiteGeneratorService()
    with patch(
        "core.services.website_generator_service.get_storage_provider",
        return_value=mock_storage,
    ):
        files = await service.generate_website(
            portfolio=portfolio,
            subdomain="janedoe",
            user=user,
            profile=profile,
            config=config,
        )

    assert "favicon.webp" in files
    assert files["favicon.webp"]["binary"] is True
    assert len(files["favicon.webp"]["content"]) > 0
    assert "apple-touch-icon.webp" in files
    assert 'href="favicon.webp"' in files["index.html"]
    assert 'href="apple-touch-icon.webp"' in files["index.html"]
    mock_storage.get_file.assert_awaited_once_with("profile_pictures/test-user.png")


@pytest.mark.anyio
@pytest.mark.parametrize("theme_id", ["bento", "neon"])
async def test_generator_renders_creative_themes(theme_id, beanie_db):
    user = make_user()
    profile = make_profile(user_id=user.id)
    portfolio = make_portfolio(user_id=user.id, profile_id=profile.id)
    config = WebsiteConfig(theme=theme_id, chatbot_enabled=True)

    service = WebsiteGeneratorService()
    files = await service.generate_website(
        portfolio=portfolio,
        subdomain="janedoe",
        user=user,
        profile=profile,
        config=config,
    )

    assert "index.html" in files
    assert "style.css" in files
    assert "script.js" in files
    assert "favicon.webp" in files
    assert 'href="favicon.webp"' in files["index.html"]
    assert "YARBA_CHAT" in files["index.html"]
    assert "chatbot.css" in files["index.html"]


@pytest.mark.anyio
async def test_generator_builds_initial_favicon_without_profile_picture(beanie_db):
    user = make_user()
    profile = make_profile(user_id=user.id)
    portfolio = make_portfolio(user_id=user.id, profile_id=profile.id)
    config = WebsiteConfig(theme="threejs", primary_color="#112233")

    service = WebsiteGeneratorService()
    files = await service.generate_website(
        portfolio=portfolio,
        subdomain="janedoe",
        user=user,
        profile=profile,
        config=config,
    )

    assert "favicon.webp" in files
    assert files["favicon.webp"]["binary"] is True
    assert len(files["favicon.webp"]["content"]) > 0
