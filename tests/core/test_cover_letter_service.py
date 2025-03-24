"""Tests for the cover letter service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId

from core.models.cover_letter import CoverLetter
from core.repositories.cover_letter_repository import (
    CoverLetterFilter,
    CoverLetterRepository,
)
from core.services.cover_letter_service import CoverLetterService


@pytest.fixture
def user_id():
    """Fixture for a user ID."""
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
def resume_id():
    """Fixture for a resume ID."""
    return PydanticObjectId()


@pytest.fixture
def cover_letter_id():
    """Fixture for a cover letter ID."""
    return PydanticObjectId()


@pytest.fixture
def mock_cover_letter_repo():
    """Fixture for a mocked cover letter repository."""
    repo = AsyncMock(spec=CoverLetterRepository)
    return repo


@pytest.fixture
def mock_user_repo():
    """Fixture for a mocked user repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_profile_repo():
    """Fixture for a mocked profile repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_portfolio_repo():
    """Fixture for a mocked portfolio repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_resume_repo():
    """Fixture for a mocked resume repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def cover_letter_service(
    mock_cover_letter_repo,
    mock_user_repo,
    mock_profile_repo,
    mock_portfolio_repo,
    mock_resume_repo,
):
    """Fixture for a cover letter service with mocked repositories."""
    return CoverLetterService(
        cover_letter_repository=mock_cover_letter_repo,
        user_repository=mock_user_repo,
        profile_repository=mock_profile_repo,
        portfolio_repository=mock_portfolio_repo,
        resume_repository=mock_resume_repo,
    )


@pytest.fixture
def sample_cover_letter(user_id, profile_id, portfolio_id, resume_id):
    """Fixture for a sample cover letter."""
    return CoverLetter(
        user_id=user_id,
        profile_id=profile_id,
        portfolio_id=portfolio_id,
        resume_id=resume_id,
        title="Sample Cover Letter",
        company_name="Test Company",
        job_title="Test Position",
        job_description="This is a test job description.",
        template_id="default",
    )


class TestCoverLetterService:
    """Test suite for CoverLetterService."""

    async def test_create_cover_letter(
        self,
        cover_letter_service,
        user_id,
        profile_id,
        portfolio_id,
        resume_id,
        mock_cover_letter_repo,
        mock_user_repo,
        mock_profile_repo,
        mock_portfolio_repo,
        mock_resume_repo,
    ):
        """Test creating a cover letter."""
        # Setup
        mock_user_repo.exists.return_value = True
        mock_profile_repo.exists.return_value = True
        mock_portfolio_repo.exists.return_value = True
        mock_resume_repo.exists.return_value = True

        mock_cover_letter = MagicMock()
        mock_cover_letter_repo.create.return_value = mock_cover_letter

        # Execute
        result = await cover_letter_service.create_cover_letter(
            user_id=user_id,
            profile_id=profile_id,
            portfolio_id=portfolio_id,
            resume_id=resume_id,
            title="Test Cover Letter",
            company_name="Test Company",
            job_title="Test Position",
            job_description="This is a test job description.",
            template_id="default",
        )

        # Assert
        assert result == mock_cover_letter
        mock_user_repo.exists.assert_called_once_with(user_id)
        mock_profile_repo.exists.assert_called_once_with(profile_id)
        mock_portfolio_repo.exists.assert_called_once_with(portfolio_id)
        mock_resume_repo.exists.assert_called_once_with(resume_id)
        mock_cover_letter_repo.create.assert_called_once()

    async def test_get_cover_letter_by_id(
        self,
        cover_letter_service,
        cover_letter_id,
        user_id,
        mock_cover_letter_repo,
        sample_cover_letter,
    ):
        """Test getting a cover letter by ID."""
        # Setup
        mock_cover_letter_repo.get_by_id.return_value = sample_cover_letter

        # Execute
        result = await cover_letter_service.get_cover_letter_by_id(
            cover_letter_id=cover_letter_id,
            user_id=user_id,
        )

        # Assert
        assert result == sample_cover_letter
        mock_cover_letter_repo.get_by_id.assert_called_once_with(cover_letter_id)

    async def test_get_cover_letter_by_id_not_found(
        self, cover_letter_service, cover_letter_id, user_id, mock_cover_letter_repo
    ):
        """Test getting a cover letter by ID when it doesn't exist."""
        # Setup
        mock_cover_letter_repo.get_by_id.return_value = None

        # Execute
        with pytest.raises(ValueError, match="Cover letter not found"):
            await cover_letter_service.get_cover_letter_by_id(
                cover_letter_id=cover_letter_id,
                user_id=user_id,
            )

        # Assert
        mock_cover_letter_repo.get_by_id.assert_called_once_with(cover_letter_id)

    async def test_get_cover_letter_by_id_wrong_user(
        self,
        cover_letter_service,
        cover_letter_id,
        user_id,
        mock_cover_letter_repo,
        sample_cover_letter,
    ):
        """Test getting a cover letter by ID with wrong user."""
        # Setup
        different_user_id = PydanticObjectId()
        sample_cover_letter.user_id = different_user_id
        mock_cover_letter_repo.get_by_id.return_value = sample_cover_letter

        # Execute
        with pytest.raises(ValueError, match="Cover letter does not belong to user"):
            await cover_letter_service.get_cover_letter_by_id(
                cover_letter_id=cover_letter_id,
                user_id=user_id,
            )

        # Assert
        mock_cover_letter_repo.get_by_id.assert_called_once_with(cover_letter_id)

    async def test_filter_cover_letters(
        self, cover_letter_service, user_id, mock_cover_letter_repo, sample_cover_letter
    ):
        """Test filtering cover letters."""
        # Setup
        mock_cover_letter_repo.get_by_filter.return_value = [sample_cover_letter]
        filter_params = CoverLetterFilter(title_contains="Sample")

        # Execute
        result = await cover_letter_service.filter_cover_letters(
            user_id=user_id,
            filter_params=filter_params,
        )

        # Assert
        assert result == [sample_cover_letter]
        mock_cover_letter_repo.get_by_filter.assert_called_once()

    async def test_update_cover_letter(
        self,
        cover_letter_service,
        cover_letter_id,
        user_id,
        mock_cover_letter_repo,
        sample_cover_letter,
    ):
        """Test updating a cover letter."""
        # Setup
        mock_cover_letter_repo.get_by_id.return_value = sample_cover_letter
        mock_cover_letter_repo.update.return_value = sample_cover_letter

        # Execute
        result = await cover_letter_service.update_cover_letter(
            cover_letter_id=cover_letter_id,
            user_id=user_id,
            title="Updated Title",
        )

        # Assert
        assert result == sample_cover_letter
        mock_cover_letter_repo.get_by_id.assert_called_once_with(cover_letter_id)
        mock_cover_letter_repo.update.assert_called_once()

    async def test_delete_cover_letter(
        self,
        cover_letter_service,
        cover_letter_id,
        user_id,
        mock_cover_letter_repo,
        sample_cover_letter,
    ):
        """Test deleting a cover letter."""
        # Setup
        mock_cover_letter_repo.get_by_id.return_value = sample_cover_letter
        mock_cover_letter_repo.delete.return_value = True

        # Execute
        result = await cover_letter_service.delete_cover_letter(
            cover_letter_id=cover_letter_id,
            user_id=user_id,
        )

        # Assert
        assert result is True
        mock_cover_letter_repo.get_by_id.assert_called_once_with(cover_letter_id)
        mock_cover_letter_repo.delete.assert_called_once_with(cover_letter_id)
