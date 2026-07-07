"""Tests for public API base URL resolution."""

from config.settings import Settings


def test_public_api_base_url_uses_api_base_url_env():
    settings = Settings().model_copy(
        update={
            "auth": Settings().auth.model_copy(
                update={"api_base_url": "https://api.yarba.app"}
            ),
        }
    )
    assert settings.public_api_base_url == "https://api.yarba.app"
