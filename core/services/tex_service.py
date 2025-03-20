"""Service for TeX templates, headers, and preambles."""

from typing import Dict, List, Optional

from config.logging_config import get_logger

from ..models.preamble import Preamble
from ..models.tex_header import TexHeader
from ..models.tex_template import TexTemplate
from ..repositories.preamble import PreambleRepository
from ..repositories.tex_header import TexHeaderRepository
from ..repositories.tex_template import TexTemplateRepository

logger = get_logger(__name__)


class TexService:
    """Service for working with LaTeX templates, headers, and preambles."""

    def __init__(self):
        """Initialize the TeX service."""
        self.template_repo = TexTemplateRepository()
        self.header_repo = TexHeaderRepository()
        self.preamble_repo = PreambleRepository()
        self.logger = get_logger(self.__class__.__name__)

    # Template methods
    async def get_template(self, name: str) -> Optional[TexTemplate]:
        """
        Get a template by name.

        Args:
            name: Name of the template

        Returns:
            The template if found, None otherwise
        """
        return await self.template_repo.get_by_name(name)

    async def get_template_by_type(
        self, template_type: str = "resume", default_only: bool = False
    ) -> List[TexTemplate]:
        """
        Get templates by type.

        Args:
            template_type: Type of templates to get
            default_only: If True, return only the default template

        Returns:
            List of templates (or a single template if default_only is True)
        """
        if default_only:
            default = await self.template_repo.get_default(template_type)
            return [default] if default else []
        else:
            return await self.template_repo.get_all_by_type(template_type)

    async def format_template(self, template_name: str, **kwargs) -> Optional[str]:
        """
        Format a template with given parameters.

        Args:
            template_name: Name of the template to format
            **kwargs: Parameters to use in formatting

        Returns:
            Formatted template string if successful, None otherwise
        """
        template = await self.get_template(template_name)
        if not template:
            self.logger.warning(f"Template not found: {template_name}")
            return None

        try:
            return self.template_repo.safe_format_template(template, **kwargs)
        except ValueError as e:
            self.logger.error(f"Error formatting template: {e}")
            return None

    # Header methods
    async def get_header(
        self, name: str, category: str = "resume_section"
    ) -> Optional[TexHeader]:
        """
        Get a header by name and category.

        Args:
            name: Name of the header
            category: Category of the header

        Returns:
            The header if found, None otherwise
        """
        return await self.header_repo.get_by_name(name, category)

    async def get_default_header(
        self, name: str, category: str = "resume_section"
    ) -> Optional[TexHeader]:
        """
        Get the default header for a name and category.

        Args:
            name: Name of the header
            category: Category of the header

        Returns:
            The default header if found, None otherwise
        """
        return await self.header_repo.get_default(name, category)

    async def get_headers_by_category(
        self, category: str = "resume_section"
    ) -> List[TexHeader]:
        """
        Get all headers for a category.

        Args:
            category: Category of headers to get

        Returns:
            List of headers
        """
        return await self.header_repo.get_all_by_category(category)

    # Preamble methods
    async def get_preamble(
        self, name: str, preamble_type: str = "resume_preamble"
    ) -> Optional[Preamble]:
        """
        Get a preamble by name and type.

        Args:
            name: Name of the preamble
            preamble_type: Type of the preamble

        Returns:
            The preamble if found, None otherwise
        """
        return await self.preamble_repo.get_by_name(name, preamble_type)

    async def get_default_preamble(
        self, preamble_type: str = "resume_preamble"
    ) -> Optional[Preamble]:
        """
        Get the default preamble for a type.

        Args:
            preamble_type: Type of preamble

        Returns:
            The default preamble if found, None otherwise
        """
        return await self.preamble_repo.get_default(preamble_type)

    async def get_preambles_by_type(
        self, preamble_type: str = "resume_preamble"
    ) -> List[Preamble]:
        """
        Get all preambles for a type.

        Args:
            preamble_type: Type of preambles to get

        Returns:
            List of preambles
        """
        return await self.preamble_repo.get_by_type(preamble_type)

    # Cache management
    def clear_caches(self) -> None:
        """Clear all repository caches."""
        self.template_repo.clear_cache()
        self.header_repo.clear_cache()
        self.logger.debug("All TeX caches cleared")
