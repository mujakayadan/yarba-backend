"""Tests for the TexService class."""

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from beanie import init_beanie

from core.models.preamble import Preamble
from core.models.tex_header import TexHeader
from core.models.tex_template import TexTemplate
from core.services.tex_service import TexService


# Make sure tests can import from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.mark.asyncio
class TestTexService:
    """Test class for the TexService."""

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
        self.service = TexService()
        
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
        self.service.template_repo.safe_format_template = MagicMock(return_value="Hello World!")
        
        # Execute
        result = await self.service.format_template("test_template", name="World")
        
        # Verify
        self.service.template_repo.get_by_name.assert_called_once_with("test_template")
        self.service.template_repo.safe_format_template.assert_called_once()
        assert result == "Hello World!"
        
    async def test_get_header(self):
        """Test getting a header by name and category."""
        # Setup
        header = TexHeader(name="test_header", content="Test content", category="resume_section")
        self.service.header_repo.get_by_name = AsyncMock(return_value=header)
        
        # Execute
        result = await self.service.get_header("test_header", "resume_section")
        
        # Verify
        self.service.header_repo.get_by_name.assert_called_once_with("test_header", "resume_section")
        assert result == header
        
    async def test_get_default_preamble(self):
        """Test getting the default preamble for a type."""
        # Setup
        preamble = Preamble(name="default", content="Test content", type="resume_preamble", is_default=True)
        self.service.preamble_repo.get_default = AsyncMock(return_value=preamble)
        
        # Execute
        result = await self.service.get_default_preamble("resume_preamble")
        
        # Verify
        self.service.preamble_repo.get_default.assert_called_once_with("resume_preamble")
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