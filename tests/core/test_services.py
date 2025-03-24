"""Tests for core services."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.exceptions.base import (
    BadRequestException,
    NotFoundException,
    UnauthorizedException,
)
from core.services.auth_service import AuthService
from core.services.cover_letter_generation_service import CoverLetterGenerationService
from core.services.latex_service import LatexService
from core.services.resume_generation_service import ResumeGenerationService
from core.services.resume_service import ResumeService


@pytest.fixture
def mock_user_repository():
    """Fixture for mocking user repository."""
    repository = AsyncMock()
    repository.get_by_email = AsyncMock()
    repository.create = AsyncMock()
    repository.get_by_id = AsyncMock()
    return repository


@pytest.fixture
def mock_resume_repository():
    """Fixture for mocking resume repository."""
    repository = AsyncMock()
    repository.get_by_id = AsyncMock()
    repository.get_all = AsyncMock()
    repository.create = AsyncMock()
    repository.update = AsyncMock()
    repository.delete = AsyncMock()
    return repository


@pytest.fixture
def mock_cover_letter_repository():
    """Fixture for mocking cover letter repository."""
    repository = AsyncMock()
    repository.get_by_id = AsyncMock()
    repository.get_all = AsyncMock()
    repository.create = AsyncMock()
    repository.update = AsyncMock()
    repository.delete = AsyncMock()
    return repository


@pytest.fixture
def mock_portfolio_repository():
    """Fixture for mocking portfolio repository."""
    repository = AsyncMock()
    repository.get_by_id = AsyncMock()
    repository.get_all = AsyncMock()
    repository.create = AsyncMock()
    repository.update = AsyncMock()
    repository.delete = AsyncMock()
    return repository


@pytest.fixture
def mock_profile_repository():
    """Fixture for mocking profile repository."""
    repository = AsyncMock()
    repository.get_by_id = AsyncMock()
    repository.get_by_user_id = AsyncMock()
    repository.get_all = AsyncMock()
    repository.create = AsyncMock()
    repository.update = AsyncMock()
    repository.delete = AsyncMock()
    return repository


@pytest.fixture
def mock_llm_service():
    """Fixture for mocking LLM service."""
    service = AsyncMock()
    service.generate_text = AsyncMock()
    return service


@pytest.fixture
def mock_latex_service():
    """Fixture for mocking LaTeX service."""
    service = AsyncMock()
    service.generate_pdf = AsyncMock()
    return service


@pytest.fixture
def mock_tex_service():
    """Fixture for mocking TeX service."""
    service = AsyncMock()
    service.generate_resume_latex = AsyncMock()
    service.generate_cover_letter_latex = AsyncMock()
    return service


class TestAuthService:
    """Tests for AuthService."""

    @pytest.mark.asyncio
    async def test_register_user_success(self, mock_user_repository):
        """Test successful user registration."""
        # Arrange
        mock_user_repository.get_by_email.return_value = None
        mock_user_repository.create.return_value = {
            "id": "123",
            "email": "test@example.com",
        }

        auth_service = AuthService(user_repository=mock_user_repository)

        # Act
        result = await auth_service.register_user(
            email="test@example.com",
            password="Password123!",
            full_name="Test User",
        )

        # Assert
        assert result["id"] == "123"
        assert result["email"] == "test@example.com"
        mock_user_repository.get_by_email.assert_called_once_with("test@example.com")
        mock_user_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_user_email_exists(self, mock_user_repository):
        """Test user registration with existing email."""
        # Arrange
        mock_user_repository.get_by_email.return_value = {
            "id": "123",
            "email": "test@example.com",
        }

        auth_service = AuthService(user_repository=mock_user_repository)

        # Act & Assert
        with pytest.raises(BadRequestException) as excinfo:
            await auth_service.register_user(
                email="test@example.com",
                password="Password123!",
                full_name="Test User",
            )

        assert "Email already registered" in str(excinfo.value)
        mock_user_repository.get_by_email.assert_called_once_with("test@example.com")
        mock_user_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_login_user_success(self, mock_user_repository):
        """Test successful user login."""
        # Arrange
        # Mock a user with a hashed password
        with patch("core.utils.password.verify_password") as mock_verify:
            mock_verify.return_value = True
            mock_user_repository.get_by_email.return_value = {
                "id": "123",
                "email": "test@example.com",
                "hashed_password": "hashed_password",
            }

            auth_service = AuthService(user_repository=mock_user_repository)

            # Act
            with patch("core.utils.jwt.create_access_token") as mock_create_token:
                mock_create_token.return_value = "test_token"
                result = await auth_service.login_user(
                    email="test@example.com",
                    password="Password123!",
                )

            # Assert
            assert result["access_token"] == "test_token"
            assert result["token_type"] == "bearer"
            mock_user_repository.get_by_email.assert_called_once_with(
                "test@example.com"
            )
            mock_verify.assert_called_once()
            mock_create_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, mock_user_repository):
        """Test user login with non-existent email."""
        # Arrange
        mock_user_repository.get_by_email.return_value = None

        auth_service = AuthService(user_repository=mock_user_repository)

        # Act & Assert
        with pytest.raises(UnauthorizedException) as excinfo:
            await auth_service.login_user(
                email="test@example.com",
                password="Password123!",
            )

        assert "Invalid credentials" in str(excinfo.value)
        mock_user_repository.get_by_email.assert_called_once_with("test@example.com")

    @pytest.mark.asyncio
    async def test_login_user_invalid_password(self, mock_user_repository):
        """Test user login with invalid password."""
        # Arrange
        # Mock a user with a hashed password
        with patch("core.utils.password.verify_password") as mock_verify:
            mock_verify.return_value = False
            mock_user_repository.get_by_email.return_value = {
                "id": "123",
                "email": "test@example.com",
                "hashed_password": "hashed_password",
            }

            auth_service = AuthService(user_repository=mock_user_repository)

            # Act & Assert
            with pytest.raises(UnauthorizedException) as excinfo:
                await auth_service.login_user(
                    email="test@example.com",
                    password="WrongPassword",
                )

            assert "Invalid credentials" in str(excinfo.value)
            mock_user_repository.get_by_email.assert_called_once_with(
                "test@example.com"
            )
            mock_verify.assert_called_once()


class TestResumeService:
    """Tests for ResumeService."""

    @pytest.mark.asyncio
    async def test_create_resume_success(
        self, mock_resume_repository, mock_user_repository
    ):
        """Test successful resume creation."""
        # Arrange
        mock_user_repository.get_by_id.return_value = {
            "id": "user123",
            "email": "test@example.com",
        }
        mock_resume_repository.create.return_value = {
            "id": "resume123",
            "title": "Test Resume",
            "user_id": "user123",
        }

        resume_service = ResumeService(
            resume_repository=mock_resume_repository,
            user_repository=mock_user_repository,
        )

        # Act
        result = await resume_service.create_resume(
            user_id="user123",
            title="Test Resume",
            template_id="default",
        )

        # Assert
        assert result["id"] == "resume123"
        assert result["title"] == "Test Resume"
        assert result["user_id"] == "user123"
        mock_user_repository.get_by_id.assert_called_once_with("user123")
        mock_resume_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_resume_user_not_found(
        self, mock_resume_repository, mock_user_repository
    ):
        """Test resume creation with non-existent user."""
        # Arrange
        mock_user_repository.get_by_id.return_value = None

        resume_service = ResumeService(
            resume_repository=mock_resume_repository,
            user_repository=mock_user_repository,
        )

        # Act & Assert
        with pytest.raises(NotFoundException) as excinfo:
            await resume_service.create_resume(
                user_id="user123",
                title="Test Resume",
                template_id="default",
            )

        assert "User not found" in str(excinfo.value)
        mock_user_repository.get_by_id.assert_called_once_with("user123")
        mock_resume_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_resume_by_id_success(self, mock_resume_repository):
        """Test successful resume retrieval by ID."""
        # Arrange
        mock_resume_repository.get_by_id.return_value = {
            "id": "resume123",
            "title": "Test Resume",
            "user_id": "user123",
        }

        resume_service = ResumeService(
            resume_repository=mock_resume_repository,
            user_repository=AsyncMock(),
        )

        # Act
        result = await resume_service.get_resume_by_id(
            resume_id="resume123",
            user_id="user123",
        )

        # Assert
        assert result["id"] == "resume123"
        assert result["title"] == "Test Resume"
        assert result["user_id"] == "user123"
        mock_resume_repository.get_by_id.assert_called_once_with("resume123")

    @pytest.mark.asyncio
    async def test_get_resume_by_id_not_found(self, mock_resume_repository):
        """Test resume retrieval with non-existent ID."""
        # Arrange
        mock_resume_repository.get_by_id.return_value = None

        resume_service = ResumeService(
            resume_repository=mock_resume_repository,
            user_repository=AsyncMock(),
        )

        # Act & Assert
        with pytest.raises(NotFoundException) as excinfo:
            await resume_service.get_resume_by_id(
                resume_id="resume123",
                user_id="user123",
            )

        assert "Resume not found" in str(excinfo.value)
        mock_resume_repository.get_by_id.assert_called_once_with("resume123")

    @pytest.mark.asyncio
    async def test_get_resume_by_id_unauthorized(self, mock_resume_repository):
        """Test resume retrieval with unauthorized user."""
        # Arrange
        mock_resume_repository.get_by_id.return_value = {
            "id": "resume123",
            "title": "Test Resume",
            "user_id": "other_user",
        }

        resume_service = ResumeService(
            resume_repository=mock_resume_repository,
            user_repository=AsyncMock(),
        )

        # Act & Assert
        with pytest.raises(UnauthorizedException) as excinfo:
            await resume_service.get_resume_by_id(
                resume_id="resume123",
                user_id="user123",
            )

        assert "not authorized" in str(excinfo.value)
        mock_resume_repository.get_by_id.assert_called_once_with("resume123")


class TestLaTeXService:
    """Tests for LaTeXService."""

    def test_generate_pdf_success(self):
        """Test successful PDF generation."""
        # Arrange
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            with patch("os.path.exists") as mock_exists:
                mock_exists.return_value = True

                with patch("builtins.open", MagicMock()):
                    latex_service = LatexService()

                    # Act
                    result = latex_service.generate_pdf(
                        template_name="default",
                        output_filename="test_resume",
                        template_data={
                            "name": "Test User",
                            "email": "test@example.com",
                        },
                    )

                    # Assert
                    assert result["success"] is True
                    assert "pdf_path" in result
                    mock_run.assert_called_once()
                    mock_exists.assert_called_once()

    def test_generate_pdf_compilation_error(self):
        """Test PDF generation with compilation error."""
        # Arrange
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)

            latex_service = LatexService()

            # Act
            result = latex_service.generate_pdf(
                template_name="default",
                output_filename="test_resume",
                template_data={
                    "name": "Test User",
                    "email": "test@example.com",
                },
            )

            # Assert
            assert result["success"] is False
            assert "error" in result
            mock_run.assert_called_once()


class TestResumeGenerationService:
    """Tests for ResumeGenerationService."""

    @pytest.mark.asyncio
    async def test_generate_resume_content_success(
        self,
        mock_llm_service,
        mock_resume_repository,
        mock_profile_repository,
        mock_portfolio_repository,
        mock_tex_service,
    ):
        """Test successful resume content generation."""
        # Arrange
        mock_llm_service.generate_text.return_value = "Generated resume content"

        # Mock the profile and portfolio data
        mock_profile_repository.get_by_user_id.return_value = {
            "id": "profile123",
            "user_id": "user123",
            "full_name": "Test User",
            "email": "test@example.com",
        }

        mock_portfolio_repository.get_by_user_id.return_value = [
            {
                "id": "portfolio123",
                "user_id": "user123",
                "skills": ["Python", "FastAPI"],
                "experience": [{"company": "Company X", "years": 5}],
            }
        ]

        # Mock resume repository responses
        mock_resume_repository.create.return_value = {
            "id": "resume123",
            "user_id": "user123",
            "profile_id": "profile123",
            "portfolio_id": "portfolio123",
            "content": "Generated resume content",
        }

        resume_generation_service = ResumeGenerationService(
            resume_repository=mock_resume_repository,
            profile_repository=mock_profile_repository,
            portfolio_repository=mock_portfolio_repository,
            llm_service=mock_llm_service,
            tex_service=mock_tex_service,
        )

        # Act
        result = await resume_generation_service.generate_resume_content(
            user_id="user123",
            job_description="Software Developer position",
            selected_sections={"experience": "process", "education": "process"},
        )

        # Assert
        assert result == "Generated resume content"
        mock_llm_service.generate_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_pdf_success(
        self,
        mock_llm_service,
        mock_resume_repository,
        mock_profile_repository,
        mock_portfolio_repository,
        mock_tex_service,
    ):
        """Test successful PDF generation for a resume."""
        # Arrange
        mock_resume_repository.get_by_id.return_value = {
            "id": "resume123",
            "user_id": "user123",
            "profile_id": "profile123",
            "portfolio_id": "portfolio123",
            "content": "Resume content",
        }

        # Mock the TeX service
        mock_tex_service.generate_resume_latex.return_value = "LaTeX content"

        # Mock the LaTeX service PDF generation
        with patch(
            "core.services.resume_generation_service.LatexService"
        ) as mock_latex_service_class:
            mock_latex_service = mock_latex_service_class.return_value
            mock_latex_service.generate_pdf.return_value = {
                "success": True,
                "pdf_path": "/tmp/resume.pdf",
                "pdf_content": b"PDF content",
            }

            resume_generation_service = ResumeGenerationService(
                resume_repository=mock_resume_repository,
                profile_repository=mock_profile_repository,
                portfolio_repository=mock_portfolio_repository,
                llm_service=mock_llm_service,
                tex_service=mock_tex_service,
            )

            # Act
            result = await resume_generation_service.generate_pdf(
                resume_id="resume123",
                user_id="user123",
            )

            # Assert
            assert result == b"PDF content"
            mock_resume_repository.get_by_id.assert_called_once_with("resume123")
            mock_tex_service.generate_resume_latex.assert_called_once()
            mock_latex_service.generate_pdf.assert_called_once()


class TestCoverLetterGenerationService:
    """Tests for CoverLetterGenerationService."""

    @pytest.mark.asyncio
    async def test_generate_cover_letter_content_success(
        self,
        mock_llm_service,
        mock_cover_letter_repository,
        mock_resume_repository,
        mock_profile_repository,
        mock_portfolio_repository,
        mock_tex_service,
    ):
        """Test successful cover letter content generation."""
        # Arrange
        mock_llm_service.generate_text.return_value = "Generated cover letter content"

        # Mock the profile and portfolio data
        mock_profile_repository.get_by_user_id.return_value = {
            "id": "profile123",
            "user_id": "user123",
            "full_name": "Test User",
            "email": "test@example.com",
        }

        mock_portfolio_repository.get_by_user_id.return_value = [
            {
                "id": "portfolio123",
                "user_id": "user123",
                "skills": ["Python", "FastAPI"],
                "experience": [{"company": "Company X", "years": 5}],
            }
        ]

        # Mock resume data if needed
        mock_resume_repository.get_by_id.return_value = {
            "id": "resume123",
            "user_id": "user123",
            "content": "Resume content for reference",
        }

        # Mock cover letter repository responses
        mock_cover_letter_repository.create.return_value = {
            "id": "cover_letter123",
            "user_id": "user123",
            "profile_id": "profile123",
            "portfolio_id": "portfolio123",
            "resume_id": "resume123",
            "content": "Generated cover letter content",
        }

        cover_letter_generation_service = CoverLetterGenerationService(
            cover_letter_repository=mock_cover_letter_repository,
            resume_repository=mock_resume_repository,
            profile_repository=mock_profile_repository,
            portfolio_repository=mock_portfolio_repository,
            llm_service=mock_llm_service,
            tex_service=mock_tex_service,
        )

        # Act
        result = await cover_letter_generation_service.generate_cover_letter_content(
            user_id="user123",
            job_description="Software Developer position",
            resume_id="resume123",
            company_name="Test Company",
            job_title="Software Engineer",
        )

        # Assert
        assert result == "Generated cover letter content"
        mock_llm_service.generate_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_pdf_success(
        self,
        mock_llm_service,
        mock_cover_letter_repository,
        mock_resume_repository,
        mock_profile_repository,
        mock_portfolio_repository,
        mock_tex_service,
    ):
        """Test successful PDF generation for a cover letter."""
        # Arrange
        mock_cover_letter_repository.get_by_id.return_value = {
            "id": "cover_letter123",
            "user_id": "user123",
            "profile_id": "profile123",
            "portfolio_id": "portfolio123",
            "resume_id": "resume123",
            "content": "Cover letter content",
            "cover_letter_content": "Formatted cover letter content",
        }

        # Mock the TeX service
        mock_tex_service.generate_cover_letter_latex.return_value = "LaTeX content"

        # Mock the LaTeX service PDF generation
        with patch(
            "core.services.cover_letter_generation_service.LatexService"
        ) as mock_latex_service_class:
            mock_latex_service = mock_latex_service_class.return_value
            mock_latex_service.generate_pdf.return_value = {
                "success": True,
                "pdf_path": "/tmp/cover_letter.pdf",
                "pdf_content": b"PDF content",
            }

            cover_letter_generation_service = CoverLetterGenerationService(
                cover_letter_repository=mock_cover_letter_repository,
                resume_repository=mock_resume_repository,
                profile_repository=mock_profile_repository,
                portfolio_repository=mock_portfolio_repository,
                llm_service=mock_llm_service,
                tex_service=mock_tex_service,
            )

            # Act
            result = await cover_letter_generation_service.generate_pdf(
                cover_letter_id="cover_letter123",
                user_id="user123",
            )

            # Assert
            assert result == b"PDF content"
            mock_cover_letter_repository.get_by_id.assert_called_once_with(
                "cover_letter123"
            )
            mock_tex_service.generate_cover_letter_latex.assert_called_once()
            mock_latex_service.generate_pdf.assert_called_once()
