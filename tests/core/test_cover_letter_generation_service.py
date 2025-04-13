"""Tests for the cover letter generation service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId

from core.models.cover_letter import CoverLetter
from core.services.cover_letter_generation_service import CoverLetterGenerationService


@pytest.fixture
def user_id():
    """Fixture for a user ID."""
    return PydanticObjectId()


@pytest.fixture
def cover_letter_id():
    """Fixture for a cover letter ID."""
    return PydanticObjectId()


@pytest.fixture
def resume_id():
    """Fixture for a resume ID."""
    return PydanticObjectId()


@pytest.fixture
def profile_id():
    """Fixture for a profile ID."""
    return PydanticObjectId()


@pytest.fixture
def portfolio_id():
    """Fixture for a portfolio ID."""
    return PydanticObjectId()


@pytest.fixture
def mock_cover_letter_service():
    """Fixture for a mocked cover letter service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_portfolio_service():
    """Fixture for a mocked portfolio service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_profile_service():
    """Fixture for a mocked profile service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_resume_service():
    """Fixture for a mocked resume service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_preamble_service():
    """Fixture for a mocked preamble service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_tex_header_service():
    """Fixture for a mocked tex header service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_llm_service():
    """Fixture for a mocked LLM service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_tex_service():
    """Fixture for a mocked TeX service."""
    service = AsyncMock()
    return service


@pytest.fixture
def sample_cover_letter(user_id, profile_id, portfolio_id, resume_id):
    """Sample cover letter for testing."""
    return MagicMock(
        id=cover_letter_id,
        user_id=user_id,
        profile_id=profile_id,
        portfolio_id=portfolio_id,
        resume_id=resume_id,
        title="Test Cover Letter",
        company_name="Test Company",
        job_title="Test Job",
        job_description="Test job description",
        content={},
        cover_letter_content=None,
        cover_letter_pdf_key=None,
        template_id="default",
    )


@pytest.fixture
def generation_service(
    mock_cover_letter_service,
    mock_portfolio_service,
    mock_profile_service,
    mock_resume_service,
    mock_preamble_service,
    mock_tex_header_service,
    mock_llm_service,
    mock_tex_service,
):
    """Fixture for a cover letter generation service with mocked dependencies."""
    return CoverLetterGenerationService(
        cover_letter_service=mock_cover_letter_service,
        portfolio_service=mock_portfolio_service,
        profile_service=mock_profile_service,
        resume_service=mock_resume_service,
        preamble_service=mock_preamble_service,
        tex_header_service=mock_tex_header_service,
        llm_service=mock_llm_service,
        tex_service=mock_tex_service,
    )


@pytest.fixture
def settings():
    """Fixture for settings."""
    return MagicMock(llm=MagicMock(default_model="gpt-4"))


class TestCoverLetterGenerationService:
    """Test suite for CoverLetterGenerationService."""

    @patch(
        "core.services.cover_letter_generation_service.settings", new_callable=MagicMock
    )
    async def test_generate_cover_letter_content(
        self,
        mock_settings,
        generation_service,
        cover_letter_id,
        mock_cover_letter_service,
        mock_portfolio_service,
        mock_profile_service,
        mock_llm_service,
        sample_cover_letter,
    ):
        """Test generating cover letter content."""
        # Setup
        mock_settings.llm.default_model = "gpt-4"
        mock_cover_letter_service.get_cover_letter_by_id.return_value = (
            sample_cover_letter
        )
        mock_portfolio = MagicMock()
        mock_portfolio_service.get_portfolio.return_value = mock_portfolio
        mock_profile = MagicMock()
        mock_profile_service.get_profile.return_value = mock_profile
        mock_llm_service.generate_text.return_value = "Generated cover letter content"

        # Execute
        await generation_service.generate_cover_letter_content(
            cover_letter_id=cover_letter_id,
            regenerate=False,
        )

        # Assert
        mock_cover_letter_service.get_cover_letter_by_id.assert_called_once()
        mock_portfolio_service.get_portfolio.assert_called_once()
        mock_profile_service.get_profile.assert_called_once()
        mock_llm_service.generate_text.assert_called_once()
        mock_cover_letter_service.update_cover_letter.assert_called_once()

    @patch(
        "core.services.cover_letter_generation_service.settings", new_callable=MagicMock
    )
    async def test_generate_cover_letter_content_with_existing_content(
        self,
        mock_settings,
        generation_service,
        cover_letter_id,
        mock_cover_letter_service,
        sample_cover_letter,
    ):
        """Test generating cover letter content when content already exists."""
        # Setup
        mock_settings.llm.default_model = "gpt-4"
        sample_cover_letter.content = "Existing content"
        mock_cover_letter_service.get_cover_letter_by_id.return_value = (
            sample_cover_letter
        )

        # Execute
        await generation_service.generate_cover_letter_content(
            cover_letter_id=cover_letter_id,
            regenerate=False,
        )

        # Assert
        mock_cover_letter_service.get_cover_letter_by_id.assert_called_once()
        mock_cover_letter_service.update_cover_letter.assert_not_called()

    @patch(
        "core.services.cover_letter_generation_service.settings", new_callable=MagicMock
    )
    async def test_generate_cover_letter_content_force_regenerate(
        self,
        mock_settings,
        generation_service,
        cover_letter_id,
        mock_cover_letter_service,
        mock_portfolio_service,
        mock_profile_service,
        mock_llm_service,
        sample_cover_letter,
    ):
        """Test forcing regeneration of cover letter content."""
        # Setup
        mock_settings.llm.default_model = "gpt-4"
        sample_cover_letter.content = "Existing content"
        mock_cover_letter_service.get_cover_letter_by_id.return_value = (
            sample_cover_letter
        )
        mock_portfolio = MagicMock()
        mock_portfolio_service.get_portfolio.return_value = mock_portfolio
        mock_profile = MagicMock()
        mock_profile_service.get_profile.return_value = mock_profile
        mock_llm_service.generate_text.return_value = "Regenerated cover letter content"

        # Execute
        await generation_service.generate_cover_letter_content(
            cover_letter_id=cover_letter_id,
            regenerate=True,
        )

        # Assert
        mock_cover_letter_service.get_cover_letter_by_id.assert_called_once()
        mock_portfolio_service.get_portfolio.assert_called_once()
        mock_profile_service.get_profile.assert_called_once()
        mock_llm_service.generate_text.assert_called_once()
        mock_cover_letter_service.update_cover_letter.assert_called_once()

    @patch(
        "core.services.cover_letter_generation_service.settings", new_callable=MagicMock
    )
    @patch("core.services.cover_letter_generation_service.get_storage_provider")
    async def test_generate_pdf_with_existing_pdf(
        self,
        mock_get_storage_provider,
        mock_settings,
        generation_service,
        cover_letter_id,
        mock_cover_letter_service,
        sample_cover_letter,
    ):
        """Test generating PDF when PDF already exists in S3."""
        # Setup
        mock_settings.latex.enabled = True
        sample_cover_letter.cover_letter_content = "Cover letter content"
        sample_cover_letter.cover_letter_pdf_key = "s3-key-for-pdf.pdf"
        mock_cover_letter_service.get_cover_letter_by_id.return_value = (
            sample_cover_letter
        )

        # Mock S3 storage provider
        mock_storage = MagicMock()
        mock_storage.get_url.return_value = "https://example.com/s3-key-for-pdf.pdf"
        mock_get_storage_provider.return_value = mock_storage

        # Mock httpx client
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b"PDF content from S3"
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Execute
            result = await generation_service.generate_pdf(
                cover_letter_id=cover_letter_id,
                regenerate=False,
            )

        # Assert
        assert result == b"PDF content from S3"
        mock_cover_letter_service.get_cover_letter_by_id.assert_called_once()
        mock_storage.get_url.assert_called_once_with(
            sample_cover_letter.cover_letter_pdf_key
        )

    @patch(
        "core.services.cover_letter_generation_service.settings", new_callable=MagicMock
    )
    @patch("core.services.cover_letter_generation_service.get_storage_provider")
    async def test_generate_pdf_force_regenerate(
        self,
        mock_get_storage_provider,
        mock_settings,
        generation_service,
        cover_letter_id,
        mock_cover_letter_service,
        mock_tex_service,
        sample_cover_letter,
    ):
        """Test forcing regeneration of PDF even when one exists in S3."""
        # Setup
        mock_settings.latex.enabled = True
        sample_cover_letter.cover_letter_content = "Cover letter content"
        sample_cover_letter.cover_letter_pdf_key = "old-s3-key.pdf"
        mock_cover_letter_service.get_cover_letter_by_id.return_value = (
            sample_cover_letter
        )

        # Mock LaTeX generation
        generation_service.generate_latex = AsyncMock(return_value="LaTeX content")

        # Mock PDF compilation
        mock_tex_service.compile_latex_to_pdf.return_value = b"New PDF content"

        # Mock S3 storage
        mock_storage = MagicMock()
        mock_storage.save_cover_letter_pdf.return_value = "new-s3-key.pdf"
        mock_get_storage_provider.return_value = mock_storage

        # Execute
        result = await generation_service.generate_pdf(
            cover_letter_id=cover_letter_id,
            regenerate=True,
        )

        # Assert
        assert result == b"New PDF content"
        mock_cover_letter_service.get_cover_letter_by_id.assert_called_once()
        generation_service.generate_latex.assert_called_once()
        mock_tex_service.compile_latex_to_pdf.assert_called_once()
        mock_storage.save_cover_letter_pdf.assert_called_once()
        mock_cover_letter_service.update.assert_called_once()
