"""Tests for LLM service."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId

# Make sure tests can import from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import Settings
from core.models.profile import Preferences, Profile
from core.services.llm_service import LLMService
from core.services.profile_service import ProfileService
from core.services.prompt_service import PromptService


@pytest.fixture
def mock_profile_repository():
    """Create a mock profile repository."""
    from core.repositories.profile_repository import ProfileRepository

    repo = AsyncMock(spec=ProfileRepository)
    return repo


@pytest.fixture
def mock_profile_service(mock_profile_repository):
    """Create a mock profile service."""
    service = AsyncMock(spec=ProfileService)

    # Mock a profile instead of creating an actual Profile instance
    profile = MagicMock(spec=Profile)
    profile.preferences = MagicMock(spec=Preferences)
    profile.preferences.llm_preferences = {
        "model_name": "test-model",
        "temperature": 0.5,
        "max_tokens": 1000,
    }
    profile.api_keys = {"OPENAI_API_KEY": "test_key"}

    service.get_profile_by_user_id.return_value = profile
    service.get_api_keys.return_value = {"OPENAI_API_KEY": "test_key"}
    service.profile_repository = mock_profile_repository
    return service


@pytest.fixture
def mock_prompt_service():
    """Create a mock prompt service."""
    service = AsyncMock(spec=PromptService)

    # Set up the methods that actually exist in PromptService
    service.get_prompt = AsyncMock(return_value="Test prompt")
    service.get_system_prompt = AsyncMock(return_value="You are a helpful assistant")
    service.get_cover_letter_prompt = AsyncMock(return_value="Write a cover letter")
    service.get_portfolio_section_prompt = AsyncMock(
        return_value="Generate content for section"
    )
    service.get_section_prompt = AsyncMock(return_value="Generate content for section")
    service.set_user_id = MagicMock()  # This is not async

    return service


@pytest.mark.asyncio
@patch("core.services.llm_service.litellm")
@patch("core.services.llm_service.acompletion")
async def test_llm_init(mock_acompletion, mock_litellm, mock_profile_service):
    """Test LLM service initialization."""
    # Test with default settings
    llm = LLMService(profile_service=mock_profile_service)
    assert llm.model is not None
    assert llm.temperature is not None

    # Test with custom settings
    llm = LLMService(
        profile_service=mock_profile_service, model="custom-model", temperature=0.7
    )
    assert llm.model == "custom-model"
    assert llm.temperature == 0.7


@pytest.mark.asyncio
async def test_configure_for_user(mock_profile_service, mock_prompt_service):
    """Test configuring LLM for a specific user."""
    user_id = str(PydanticObjectId())  # Convert to string for the method call

    # Reset the mock before using it
    mock_profile_service.reset_mock()

    with patch("core.services.llm_service.litellm"):
        llm = LLMService(
            profile_service=mock_profile_service,
            prompt_service=mock_prompt_service,
        )

        await llm.configure_for_user(user_id)

        # Verify profile was retrieved - use assert_called_with instead of assert_called_once_with
        mock_profile_service.get_profile_by_user_id.assert_called_with(user_id)

        # Verify user preferences were applied
        assert llm.model == "test-model"
        assert llm.temperature == 0.5
        assert llm.max_tokens == 1000

        # Verify prompt service was configured
        mock_prompt_service.set_user_id.assert_called_once_with(user_id)


@pytest.mark.asyncio
async def test_get_completion():
    """Test getting completion from LLM."""
    with patch("core.services.llm_service.litellm"):
        with patch("core.services.llm_service.acompletion") as mock_completion:
            llm = LLMService()

            # Setup mock response
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(content="Test completion"))
            ]
            mock_completion.return_value = mock_response

            # Test completion
            result = await llm.get_completion(
                prompt="Test prompt", system_prompt="Test system"
            )

            # Verify completion was called with correct params
            mock_completion.assert_called_once()
            call_args = mock_completion.call_args[1]
            assert call_args["model"] == llm.model
            assert call_args["temperature"] == llm.temperature
            assert call_args["messages"] == [
                {"role": "system", "content": "Test system"},
                {"role": "user", "content": "Test prompt"},
            ]

            # Verify result
            assert result == "Test completion"


@pytest.mark.asyncio
async def test_generate_section(mock_prompt_service):
    """Test generating section content."""
    with patch("core.services.llm_service.litellm"):
        llm = LLMService(prompt_service=mock_prompt_service)

        # Mock get_completion
        llm.get_completion = AsyncMock(return_value="Generated section")

        # Test generate section
        result = await llm.generate_section(
            section_name="work_experience",
            context={"data": "test data"},
            job_description="Test job",
        )

        # Check if get_portfolio_section_prompt is called
        # We need to check this first as the LLM service tries this first
        mock_prompt_service.get_portfolio_section_prompt.assert_called_once_with(
            "work_experience"
        )

        # Verify system prompt was retrieved
        mock_prompt_service.get_system_prompt.assert_called_once()

        # Verify result
        assert result == "Generated section"


@pytest.mark.asyncio
async def test_generate_cover_letter(mock_prompt_service):
    """Test generating cover letter."""
    with patch("core.services.llm_service.litellm"):
        llm = LLMService(prompt_service=mock_prompt_service)

        # Mock get_completion
        llm.get_completion = AsyncMock(return_value="Generated cover letter")

        # Test generate cover letter
        result = await llm.generate_cover_letter(
            resume_content={"name": "Test User"},
            job_description="Test job",
            company_name="Test Company",
            job_title="Test Title",
        )

        # Verify cover letter prompt was retrieved
        mock_prompt_service.get_cover_letter_prompt.assert_called_once()

        # Verify system prompt was retrieved
        mock_prompt_service.get_system_prompt.assert_called_once()

        # Verify result
        assert result == "Generated cover letter"
