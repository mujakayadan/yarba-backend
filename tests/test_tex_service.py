"""Tests for tex service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import init_beanie

from core.models.preamble import Preamble
from core.models.tex_header import TexHeader
from core.models.tex_template import TexTemplate
from core.repositories.preamble_repository import PreambleRepository
from core.repositories.tex_header_repository import TexHeaderRepository
from core.repositories.tex_template_repository import TexTemplateRepository
from core.services.latex_service import LatexService


@pytest.fixture
def mock_template_repository():
    """Create a mock template repository."""
    repo = AsyncMock(spec=TexTemplateRepository)
    repo.get_by_name.return_value = "Test template content with {placeholder}"
    repo.safe_format_template.return_value = "Formatted template content"
    return repo


@pytest.fixture
def mock_header_repository():
    """Create a mock header repository."""
    repo = AsyncMock(spec=TexHeaderRepository)
    repo.get_by_name.return_value = "Test header content"
    repo.get_default.return_value = "Default header content"
    return repo


@pytest.fixture
def mock_preamble_repository():
    """Create a mock preamble repository."""
    repo = AsyncMock(spec=PreambleRepository)
    repo.get_default.return_value = "Default preamble content"
    return repo


@pytest.mark.asyncio
async def test_tex_service_init(
    mock_template_repository, mock_header_repository, mock_preamble_repository
):
    """Test TeX service initialization."""
    # Create service with all dependencies
    service = LatexService(
        template_repository=mock_template_repository,
        header_repository=mock_header_repository,
        preamble_repository=mock_preamble_repository,
    )

    # Verify all dependencies are set
    assert service.template_repository == mock_template_repository
    assert service.header_repository == mock_header_repository
    assert service.preamble_repository == mock_preamble_repository


@pytest.mark.asyncio
async def test_get_template(mock_template_repository):
    """Test getting a template."""
    # Create service
    service = LatexService(template_repository=mock_template_repository)

    # Test get template
    result = await service.get_template("resume")

    # Verify repository was called
    mock_template_repository.get_by_name.assert_called_once_with("resume")

    # Verify result
    assert result == "Test template content with {placeholder}"


@pytest.mark.asyncio
async def test_format_template(mock_template_repository):
    """Test formatting a template."""
    # Create service
    service = LatexService(template_repository=mock_template_repository)

    # Test format template
    result = await service.format_template("resume", {"placeholder": "test value"})

    # Verify repository was called
    mock_template_repository.safe_format_template.assert_called_once()

    # Verify result
    assert result == "Formatted template content"


@pytest.mark.asyncio
async def test_get_header(mock_header_repository):
    """Test getting a header."""
    # Create service
    service = LatexService(header_repository=mock_header_repository)

    # Test get header
    result = await service.get_header("modern")

    # Verify repository was called
    mock_header_repository.get_by_name.assert_called_once_with("modern")

    # Verify result
    assert result == "Test header content"


@pytest.mark.asyncio
async def test_get_default_header(mock_header_repository):
    """Test getting the default header."""
    # Create service
    service = LatexService(header_repository=mock_header_repository)

    # Test get default header
    result = await service.get_default_header()

    # Verify repository was called
    mock_header_repository.get_default.assert_called_once()

    # Verify result
    assert result == "Default header content"


@pytest.mark.asyncio
async def test_get_default_preamble(mock_preamble_repository):
    async def setup_method(self):
        """Set up the test environment."""
        # Create a mock database connection
        self.db_mock = MagicMock()

        # Mock the initialization of Beanie
        with patch("beanie.init_beanie", AsyncMock()) as mock_init_beanie:
            await init_beanie(
                database=self.db_mock,
                document_models=[TexTemplate, TexHeader, Preamble],
            )

        # Initialize the service
        self.service = LatexService()

        # Mock the repositories
        self.service.template_repo = MagicMock()
        self.service.header_repo = MagicMock()
        self.service.preamble_repo = MagicMock()

    async def test_get_template(self):
        """Test getting a template by name."""
        # Setup
        template = TexTemplate(name="test_template", content="Test content")
        self.service.template_repo.get_by_name = AsyncMock(return_value=template)

        # Execute
        result = await self.service.get_template("test_template")

        # Verify
        self.service.template_repo.get_by_name.assert_called_once_with("test_template")
        assert result == template

    async def test_format_template(self):
        """Test formatting a template."""
        # Setup
        template = TexTemplate(name="test_template", content="Hello ${name}!")
        self.service.template_repo.get_by_name = AsyncMock(return_value=template)
        self.service.template_repo.safe_format_template = MagicMock(
            return_value="Hello World!"
        )

        # Execute
        result = await self.service.format_template("test_template", name="World")

        # Verify
        self.service.template_repo.get_by_name.assert_called_once_with("test_template")
        self.service.template_repo.safe_format_template.assert_called_once()
        assert result == "Hello World!"

    async def test_get_header(self):
        """Test getting a header by name and category."""
        # Setup
        header = TexHeader(
            name="test_header", content="Test content", category="resume_section"
        )
        self.service.header_repo.get_by_name = AsyncMock(return_value=header)

        # Execute
        result = await self.service.get_header("test_header", "resume_section")

        # Verify
        self.service.header_repo.get_by_name.assert_called_once_with(
            "test_header", "resume_section"
        )
        assert result == header

    async def test_get_default_preamble(self):
        """Test getting the default preamble for a type."""
        # Setup
        preamble = Preamble(
            name="default",
            content="Test content",
            type="resume_preamble",
            is_default=True,
        )
        self.service.preamble_repo.get_default = AsyncMock(return_value=preamble)

        # Execute
        result = await self.service.get_default_preamble("resume_preamble")

        # Verify
        self.service.preamble_repo.get_default.assert_called_once_with(
            "resume_preamble"
        )
        assert result == preamble

    async def test_clear_caches(self):
        """Test clearing all caches."""
        # Setup
        self.service.template_repo.clear_cache = MagicMock()
        self.service.header_repo.clear_cache = MagicMock()

        # Execute
        self.service.clear_caches()

        # Verify
        self.service.template_repo.clear_cache.assert_called_once()
        self.service.header_repo.clear_cache.assert_called_once()
