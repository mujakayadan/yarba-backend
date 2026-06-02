"""Tests for the cover letter service."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from core.exceptions.base import NotFoundException
from core.repositories.cover_letter_repository import CoverLetterFilter
from core.services.cover_letter_service import CoverLetterService
from tests.factories import make_cover_letter, make_user


@pytest.fixture
def user_id():
    return PydanticObjectId()


@pytest.fixture
def profile_id():
    return PydanticObjectId()


@pytest.fixture
def portfolio_id():
    return PydanticObjectId()


@pytest.fixture
def resume_id():
    return PydanticObjectId()


@pytest.fixture
def cover_letter_id():
    return PydanticObjectId()


@pytest.fixture
def mock_cover_letter_repo():
    return AsyncMock()


@pytest.fixture
def mock_user_repo():
    return AsyncMock()


@pytest.fixture
def mock_profile_repo():
    return AsyncMock()


@pytest.fixture
def mock_portfolio_repo():
    return AsyncMock()


@pytest.fixture
def mock_resume_repo():
    return AsyncMock()


@pytest.fixture
def cover_letter_service(
    mock_cover_letter_repo,
    mock_user_repo,
    mock_profile_repo,
    mock_portfolio_repo,
    mock_resume_repo,
):
    return CoverLetterService(
        cover_letter_repository=mock_cover_letter_repo,
        user_repository=mock_user_repo,
        profile_repository=mock_profile_repo,
        portfolio_repository=mock_portfolio_repo,
        resume_repository=mock_resume_repo,
    )


@pytest.fixture
def sample_cover_letter(user_id, profile_id, portfolio_id, resume_id):
    return make_cover_letter(
        user_id=user_id,
        profile_id=profile_id,
        portfolio_id=portfolio_id,
        resume_id=resume_id,
    )


class TestCoverLetterService:
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
        mock_user_repo.get_by_id.return_value = make_user(user_id=user_id)
        mock_resume_repo.get_by_id.return_value = MagicMock(id=resume_id)
        mock_profile_repo.exists.return_value = True
        mock_portfolio_repo.exists.return_value = True

        created = make_cover_letter(
            user_id=user_id,
            profile_id=profile_id,
            portfolio_id=portfolio_id,
            resume_id=resume_id,
        )
        mock_cover_letter_repo.create.return_value = created
        mock_resume_repo.add_cover_letter = AsyncMock()

        result = await cover_letter_service.create_cover_letter(
            user_id=user_id,
            profile_id=profile_id,
            portfolio_id=portfolio_id,
            resume_id=resume_id,
            template_id="default",
        )

        assert result == created
        mock_user_repo.get_by_id.assert_called_once_with(user_id)
        mock_resume_repo.get_by_id.assert_called_once_with(resume_id)
        mock_cover_letter_repo.create.assert_called_once()

    async def test_get_cover_letter_by_id(
        self,
        cover_letter_service,
        cover_letter_id,
        user_id,
        mock_cover_letter_repo,
        sample_cover_letter,
    ):
        sample_cover_letter.user_id = user_id
        mock_cover_letter_repo.get_by_id.return_value = sample_cover_letter

        result = await cover_letter_service.get_cover_letter_by_id(
            cover_letter_id=cover_letter_id,
            user_id=user_id,
        )

        assert result == sample_cover_letter
        mock_cover_letter_repo.get_by_id.assert_called_once_with(cover_letter_id)

    async def test_get_cover_letter_by_id_not_found(
        self, cover_letter_service, cover_letter_id, user_id, mock_cover_letter_repo
    ):
        mock_cover_letter_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundException, match="Cover letter not found"):
            await cover_letter_service.get_cover_letter_by_id(
                cover_letter_id=cover_letter_id,
                user_id=user_id,
            )

    async def test_get_cover_letter_by_id_wrong_user(
        self,
        cover_letter_service,
        cover_letter_id,
        user_id,
        mock_cover_letter_repo,
        sample_cover_letter,
    ):
        sample_cover_letter.user_id = PydanticObjectId()
        mock_cover_letter_repo.get_by_id.return_value = sample_cover_letter

        with pytest.raises(NotFoundException, match="Cover letter not found"):
            await cover_letter_service.get_cover_letter_by_id(
                cover_letter_id=cover_letter_id,
                user_id=user_id,
            )

    async def test_filter_cover_letters(
        self,
        cover_letter_service,
        user_id,
        mock_cover_letter_repo,
        mock_user_repo,
        sample_cover_letter,
    ):
        mock_user_repo.get_by_id.return_value = make_user(user_id=user_id)
        mock_cover_letter_repo.get_by_filter.return_value = [sample_cover_letter]
        filter_params = CoverLetterFilter(template_id="default")

        result = await cover_letter_service.filter_cover_letters(
            user_id=user_id,
            filter_params=filter_params,
        )

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
        sample_cover_letter.user_id = user_id
        mock_cover_letter_repo.get_by_id.return_value = sample_cover_letter
        mock_cover_letter_repo.update_metadata.return_value = sample_cover_letter

        result = await cover_letter_service.update_cover_letter(
            cover_letter_id=cover_letter_id,
            user_id=user_id,
            content="Updated body",
        )

        assert result == sample_cover_letter
        mock_cover_letter_repo.update_metadata.assert_called_once()

    async def test_delete_cover_letter(
        self,
        cover_letter_service,
        cover_letter_id,
        user_id,
        mock_cover_letter_repo,
        mock_resume_repo,
        sample_cover_letter,
    ):
        sample_cover_letter.user_id = user_id
        mock_cover_letter_repo.get_by_id.return_value = sample_cover_letter
        mock_cover_letter_repo.delete.return_value = True
        mock_resume_repo.remove_cover_letter = AsyncMock()

        result = await cover_letter_service.delete_cover_letter(
            cover_letter_id=cover_letter_id,
            user_id=user_id,
        )

        assert result is True
        mock_cover_letter_repo.delete.assert_called_once_with(cover_letter_id)
