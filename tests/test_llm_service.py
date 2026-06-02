"""Tests for LLM service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId

from core.repositories.profile_repository import ProfileRepository
from core.services.llm_service import LLMService


@pytest.fixture
def mock_profile_repository():
    return AsyncMock(spec=ProfileRepository)


@pytest.fixture
def sample_profile():
    user_id = PydanticObjectId()
    profile = MagicMock()
    profile.user_id = user_id
    profile.email = "test@example.com"
    return profile


@pytest.mark.asyncio
@patch("core.services.llm_service.litellm")
async def test_llm_init(mock_litellm, mock_profile_repository):
    llm = LLMService(profile_repository=mock_profile_repository)
    assert llm.model == "gpt-4.1"
    assert llm.temperature == 0.1
    assert llm.profile_repository is mock_profile_repository

    llm = LLMService(
        profile_repository=mock_profile_repository,
        model="custom-model",
        temperature=0.7,
    )
    assert llm.model == "custom-model"
    assert llm.temperature == 0.7


@pytest.mark.asyncio
@patch("core.services.llm_service.litellm")
async def test_configure_for_user(
    mock_litellm, mock_profile_repository, sample_profile
):
    user_id = sample_profile.user_id
    mock_profile_repository.get_by_user_id = AsyncMock(return_value=sample_profile)

    llm = LLMService(profile_repository=mock_profile_repository)
    await llm.configure_for_user(user_id)

    mock_profile_repository.get_by_user_id.assert_awaited_once_with(user_id)


@pytest.mark.asyncio
@patch("core.services.llm_service.acompletion", new_callable=AsyncMock)
@patch("core.services.llm_service.litellm")
async def test_get_completion(
    mock_litellm, mock_acompletion, mock_profile_repository, sample_profile
):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content='{"ok": true}'))]
    mock_response.usage = MagicMock(
        prompt_tokens=10, completion_tokens=5, total_tokens=15
    )
    mock_acompletion.return_value = mock_response

    llm = LLMService(profile_repository=mock_profile_repository)
    llm.check_usage_limits = AsyncMock(return_value={"can_use": True})
    result = await llm.get_completion(
        prompt="Hello",
        user_id=str(sample_profile.user_id),
        tags=["test"],
    )

    assert "llm_output" in result
    mock_acompletion.assert_awaited()


@pytest.mark.asyncio
@patch("core.services.llm_service.acompletion", new_callable=AsyncMock)
@patch("core.services.llm_service.litellm")
async def test_get_completion_json_mode(
    mock_litellm, mock_acompletion, mock_profile_repository, sample_profile
):
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content='{"personal_information": {"full_name": "Test", "email": "a@b.com"}, '
                '"career_summary": {"job_title": "Engineer", "default_summary": "Summary"}, '
                '"skills": [], "work_experience": [], "education": [], '
                '"projects": [], "publications": [], "awards": []}'
            )
        )
    ]
    mock_response.usage = MagicMock(
        prompt_tokens=10, completion_tokens=50, total_tokens=60
    )
    mock_acompletion.return_value = mock_response

    llm = LLMService(profile_repository=mock_profile_repository)
    llm.check_usage_limits = AsyncMock(return_value={"can_use": True})
    result = await llm.get_completion(
        prompt="Generate resume JSON",
        user_id=str(sample_profile.user_id),
        json_response=True,
    )

    assert "llm_output" in result
