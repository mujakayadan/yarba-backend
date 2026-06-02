"""Tests for core services."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId

from core.exceptions.base import BadRequestException, NotFoundException
from core.services.auth_service import AuthService
from core.services.cover_letter_generation_service import CoverLetterGenerationService
from core.services.latex_service import LatexService
from core.services.resume_generation_service import ResumeGenerationService
from core.services.resume_service import ResumeService
from tests.factories import make_resume, make_user


@pytest.fixture
def mock_user_repository():
    repository = AsyncMock()
    repository.get_by_email = AsyncMock()
    repository.get_by_username = AsyncMock(return_value=None)
    repository.create = AsyncMock()
    repository.get_by_id = AsyncMock()
    return repository


@pytest.fixture
def mock_resume_repository():
    repository = AsyncMock()
    repository.get_by_id = AsyncMock()
    repository.create = AsyncMock()
    repository.update = AsyncMock()
    return repository


class TestAuthService:
    @pytest.mark.asyncio
    async def test_register_with_firebase_success(self, mock_user_repository):
        mock_user_repository.get_by_email.return_value = None
        created = make_user(email="new@example.com", username="new")
        mock_user_repository.create.return_value = created

        with (
            patch(
                "core.services.auth_service.FirebaseAuth.create_user",
                new_callable=AsyncMock,
                return_value={"uid": "firebase-uid-1"},
            ),
            patch.object(
                AuthService,
                "send_verification_email",
                new_callable=AsyncMock,
            ),
            patch.object(
                AuthService,
                "create_access_token",
                return_value="jwt-token",
            ),
        ):
            auth_service = AuthService(user_repository=mock_user_repository)
            result = await auth_service.register_with_firebase(
                email="new@example.com",
                password="Password123!",
            )

        assert result["access_token"] == "jwt-token"
        assert result["user"]["email"] == "new@example.com"
        mock_user_repository.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_register_with_firebase_email_exists(self, mock_user_repository):
        mock_user_repository.get_by_email.return_value = make_user()

        auth_service = AuthService(user_repository=mock_user_repository)
        with pytest.raises(BadRequestException, match="Email already registered"):
            await auth_service.register_with_firebase(
                email="test@example.com",
                password="Password123!",
            )

    @pytest.mark.asyncio
    async def test_login_with_firebase_invalid_token(self, mock_user_repository):
        auth_service = AuthService(user_repository=mock_user_repository)
        from core.exceptions.base import UnauthorizedException

        with pytest.raises(UnauthorizedException, match="Invalid token format"):
            await auth_service.login_with_firebase(id_token="not-a-jwt")


class TestResumeService:
    @pytest.mark.asyncio
    async def test_create_resume_success(
        self, mock_resume_repository, mock_user_repository
    ):
        user = make_user()
        user.id = PydanticObjectId()
        mock_user_repository.get_by_id.return_value = user
        created = make_resume(
            user_id=user.id,
            profile_id=PydanticObjectId(),
            portfolio_id=PydanticObjectId(),
        )
        mock_resume_repository.create.return_value = created

        service = ResumeService(
            resume_repository=mock_resume_repository,
            user_repository=mock_user_repository,
        )
        result = await service.create_resume(
            user_id=user.id,
            profile_id=created.profile_id,
            portfolio_id=created.portfolio_id,
            job_description="Python role",
        )

        assert result.user_id == user.id
        mock_resume_repository.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_resume_user_not_found(
        self, mock_resume_repository, mock_user_repository
    ):
        mock_user_repository.get_by_id.return_value = None
        service = ResumeService(
            resume_repository=mock_resume_repository,
            user_repository=mock_user_repository,
        )

        with pytest.raises(NotFoundException, match="User not found"):
            await service.create_resume(
                user_id=PydanticObjectId(),
                job_description="Role",
            )

    @pytest.mark.asyncio
    async def test_get_resume_by_id_success(self, mock_resume_repository):
        user_id = PydanticObjectId()
        resume = make_resume(
            user_id=user_id,
            profile_id=PydanticObjectId(),
            portfolio_id=PydanticObjectId(),
        )
        mock_resume_repository.get_by_id.return_value = resume

        service = ResumeService(
            resume_repository=mock_resume_repository,
            user_repository=AsyncMock(),
        )
        result = await service.get_resume_by_id(resume_id=resume.id, user_id=user_id)

        assert result == resume

    @pytest.mark.asyncio
    async def test_get_resume_by_id_wrong_user(self, mock_resume_repository):
        resume = make_resume(
            user_id=PydanticObjectId(),
            profile_id=PydanticObjectId(),
            portfolio_id=PydanticObjectId(),
        )
        mock_resume_repository.get_by_id.return_value = resume

        service = ResumeService(
            resume_repository=mock_resume_repository,
            user_repository=AsyncMock(),
        )

        with pytest.raises(NotFoundException, match="Resume not found"):
            await service.get_resume_by_id(
                resume_id=resume.id,
                user_id=PydanticObjectId(),
            )


class TestLatexService:
    def test_sanitize_for_path(self):
        service = LatexService(portfolio_service=MagicMock())
        assert (
            service._sanitize_for_path("Acme Corp!", default_name="unknown")
            == "acme_corp"
        )


class TestResumeGenerationService:
    @pytest.fixture
    def generation_service(self):
        return ResumeGenerationService(
            resume_repository=AsyncMock(),
            portfolio_repository=AsyncMock(),
            profile_repository=AsyncMock(),
            prompt_service=AsyncMock(),
            profile_service=AsyncMock(),
            portfolio_service=AsyncMock(),
            llm_service=AsyncMock(),
            latex_service=AsyncMock(),
            job_service=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_generate_proper_title(self, generation_service):
        title = generation_service._generate_proper_title("Acme", "Engineer")
        assert "Acme" in title
        assert "Engineer" in title


class TestCoverLetterGenerationService:
    @pytest.fixture
    def generation_service(self):
        return CoverLetterGenerationService(
            cover_letter_repository=AsyncMock(),
            portfolio_repository=AsyncMock(),
            profile_repository=AsyncMock(),
            resume_repository=AsyncMock(),
            llm_service=AsyncMock(),
            prompt_service=AsyncMock(),
            latex_service=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_get_cover_letter_data_missing_cover_letter(self, generation_service):
        generation_service.cover_letter_repository.get_by_id = AsyncMock(
            return_value=None
        )
        with pytest.raises(ValueError, match="Cover letter with ID"):
            await generation_service.get_cover_letter_data(PydanticObjectId())
