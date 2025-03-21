"""Tests for LLM service."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from litellm.main import acompletion

from config.settings import Settings
from core.models.profile import LLMPreferences, Preferences, Profile
from core.repositories.profile import ProfileRepository
from core.services.llm import LLM
from core.services.prompt import PromptService

# Make sure tests can import from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def mock_profile_repository():
    """Create a mock profile repository."""
    repo = AsyncMock(spec=ProfileRepository)

    # Setup mock profile
    profile = Profile(
        user_id="test_user",
        preferences=MagicMock(
            llm_preferences=LLMPreferences(
                model_name="test-model", temperature=0.5, max_tokens=1000
            )
        ),
        api_keys={"OPENAI_API_KEY": "test_key"},
    )

    repo.get_by_user_id.return_value = profile
    return repo


@pytest.fixture
def mock_prompt_service():
    """Create a mock prompt service."""
    service = AsyncMock(spec=PromptService)
    service.get_prompt.return_value = "Test prompt"
    service.get_system_prompt.return_value = "You are a helpful assistant"
    service.get_cover_letter_prompt.return_value = "Write a cover letter"
    service.get_portfolio_section_prompt.return_value = "Generate content for section"
    service.get_section_prompt.return_value = "Generate content for section"
    return service


@pytest.mark.asyncio
async def test_llm_init():
    """Test LLM service initialization."""
    # Test with default settings
    llm = LLM()
    assert llm.model is not None
    assert llm.temperature is not None

    # Test with custom settings
    llm = LLM(model="custom-model", temperature=0.7, api_key="test_api_key")
    assert llm.model == "custom-model"
    assert llm.temperature == 0.7
    assert llm.api_key == "test_api_key"


@pytest.mark.asyncio
async def test_configure_for_user(mock_profile_repository, mock_prompt_service):
    """Test configuring LLM for a specific user."""
    llm = LLM(
        profile_repository=mock_profile_repository, prompt_service=mock_prompt_service
    )

    await llm.configure_for_user("test_user")

    # Verify profile was retrieved
    mock_profile_repository.get_by_user_id.assert_called_once_with("test_user")

    # Verify user preferences were applied
    assert llm.model == "test-model"
    assert llm.temperature == 0.5
    assert llm.max_tokens == 1000

    # Verify prompt service was configured
    mock_prompt_service.set_user_id.assert_called_once_with("test_user")


@pytest.mark.asyncio
async def test_get_completion():
    """Test getting completion from LLM."""
    llm = LLM()

    with patch("core.services.llm_service.acompletion") as mock_completion:
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
        assert call_args["max_tokens"] == llm.max_tokens
        assert call_args["messages"] == [
            {"role": "system", "content": "Test system"},
            {"role": "user", "content": "Test prompt"},
        ]

        # Verify result
        assert result == "Test completion"


@pytest.mark.asyncio
async def test_generate_section(mock_prompt_service):
    """Test generating section content."""
    llm = LLM(prompt_service=mock_prompt_service)

    # Mock get_completion
    llm.get_completion = AsyncMock(return_value="Generated section")

    # Test generate section
    result = await llm.generate_section(
        section_name="work_experience",
        context={"data": "test data"},
        job_description="Test job",
    )

    # Verify section prompt was retrieved
    mock_prompt_service.get_section_prompt.assert_called_once_with("work_experience")

    # Verify system prompt was retrieved
    mock_prompt_service.get_system_prompt.assert_called_once()

    # Verify result
    assert result == "Generated section"


@pytest.mark.asyncio
async def test_generate_cover_letter(mock_prompt_service):
    """Test generating cover letter."""
    llm = LLM(prompt_service=mock_prompt_service)

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


@pytest.mark.asyncio
class TestLLMService:
    """Test class for the LLMService."""

    async def setup_method(self):
        """Set up the test environment."""
        # Create mock dependencies
        self.profile_repository = MagicMock()
        self.prompt_service = MagicMock()

        # Create mock profile
        self.profile = Profile(
            user_id="user123",
            full_name="Test User",
            email="test@example.com",
            preferences=Preferences(
                llm_preferences={
                    "model_name": "claude-3-haiku-20240307",
                    "temperature": 0.5,
                    "max_tokens": 1000,
                }
            ),
            api_keys={
                "ANTHROPIC_API_KEY": "test_api_key",
            },
        )

        # Mock profile repository methods
        self.profile_repository.get_by_user_id = AsyncMock(return_value=self.profile)

        # Mock prompt service methods
        self.prompt_service.get_prompt = AsyncMock(return_value="Test prompt")
        self.prompt_service.get_section_prompt = AsyncMock(
            return_value="Test section prompt"
        )
        self.prompt_service.get_system_prompt = AsyncMock(
            return_value="Test system prompt"
        )
        self.prompt_service.get_cover_letter_prompt = AsyncMock(
            return_value="Test cover letter prompt"
        )
        self.prompt_service.set_user_id = MagicMock()

        # Initialize service with mocks
        self.service = LLM(
            profile_repository=self.profile_repository,
            prompt_service=self.prompt_service,
            model="claude-3-haiku-20240307",  # Use a specific model for testing
            api_key="test_api_key",
        )

    @patch("litellm.acompletion")
    async def test_get_completion(self, mock_acompletion):
        """Test getting a completion from the LLM."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test completion"
        mock_acompletion.return_value = mock_response

        # Execute
        result = await self.service.get_completion(
            prompt="Test prompt",
            system_prompt="Test system prompt",
        )

        # Verify
        mock_acompletion.assert_called_once()
        assert result == "Test completion"

    async def test_get_prompt(self):
        """Test getting a prompt from the prompt service."""
        # Execute
        result = await self.service.get_prompt("test_prompt")

        # Verify
        self.prompt_service.get_prompt.assert_called_once_with("test_prompt")
        assert result == "Test prompt"

    async def test_get_section_prompt(self):
        """Test getting a section prompt from the prompt service."""
        # Execute
        result = await self.service.get_section_prompt("test_section")

        # Verify
        self.prompt_service.get_portfolio_section_prompt.assert_called_once_with(
            "test_section"
        )
        assert result == "Test section prompt"

    @patch("litellm.acompletion")
    async def test_generate_section(self, mock_acompletion):
        """Test generating a section using the LLM."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated section content"
        mock_acompletion.return_value = mock_response

        # Execute
        result = await self.service.generate_section(
            section_name="work_experience",
            context={"test": "data"},
            job_description="Test job description",
        )

        # Verify
        self.prompt_service.get_portfolio_section_prompt.assert_called_once_with(
            "work_experience"
        )
        self.prompt_service.get_system_prompt.assert_called_once()
        mock_acompletion.assert_called_once()
        assert result == "Generated section content"

    @patch("litellm.acompletion")
    async def test_generate_cover_letter(self, mock_acompletion):
        """Test generating a cover letter using the LLM."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated cover letter"
        mock_acompletion.return_value = mock_response

        # Execute
        result = await self.service.generate_cover_letter(
            resume_content={"test": "data"},
            job_description="Test job description",
            company_name="Test Company",
            job_title="Test Job",
        )

        # Verify
        self.prompt_service.get_cover_letter_prompt.assert_called_once()
        self.prompt_service.get_system_prompt.assert_called_once()
        mock_acompletion.assert_called_once()
        assert result == "Generated cover letter"

    async def test_configure_for_user(self):
        """Test configuring the service for a specific user."""
        # Execute
        await self.service.configure_for_user("user123")

        # Verify
        self.profile_repository.get_by_user_id.assert_called_once_with("user123")
        self.prompt_service.set_user_id.assert_called_once_with("user123")
        assert self.service.model == "claude-3-haiku-20240307"
        assert self.service.temperature == 0.5
        assert self.service.max_tokens == 1000
