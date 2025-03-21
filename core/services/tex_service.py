"""Tex service for handling TeX templates, headers, and preambles."""

import logging
from typing import Any, Dict, List, Optional

from core.repositories.preamble_repository import (
    PreambleRepository,
    get_preamble_repository,
)
from core.repositories.tex_header_repository import (
    TexHeaderRepository,
    get_tex_header_repository,
)
from core.repositories.tex_template_repository import (
    TexTemplateRepository,
    get_tex_template_repository,
)


class TexService:
    """Service for handling TeX templates, headers, and preambles."""

    def __init__(
        self,
        header_repository: Optional[TexHeaderRepository] = None,
        template_repository: Optional[TexTemplateRepository] = None,
        preamble_repository: Optional[PreambleRepository] = None,
    ):
        """
        Initialize the Tex service.

        Args:
            header_repository: Repository for TeX headers
            template_repository: Repository for TeX templates
            preamble_repository: Repository for LaTeX preambles
        """
        self.header_repository = header_repository or get_tex_header_repository()
        self.template_repository = template_repository or get_tex_template_repository()
        self.preamble_repository = preamble_repository or get_preamble_repository()
        self.logger = logging.getLogger(__name__)

    # Template methods
    async def get_template(self, template_name: str) -> Optional[str]:
        """
        Get a template by name.

        Args:
            template_name: Name of the template

        Returns:
            Template content if found, None otherwise
        """
        template = await self.template_repository.get_by_name(template_name)
        if template:
            return template.content
        self.logger.warning(f"Template '{template_name}' not found")
        return None

    async def format_template(self, template_name: str, **kwargs) -> Optional[str]:
        """
        Format a template with the given parameters.

        Args:
            template_name: Name of the template
            **kwargs: Parameters to format the template with

        Returns:
            Formatted template if successful, None otherwise
        """
        try:
            template = await self.template_repository.get_by_name(template_name)
            if not template:
                self.logger.warning(f"Template '{template_name}' not found")
                return None

            return self.template_repository.safe_format_template(template, **kwargs)
        except ValueError as e:
            self.logger.error(f"Error formatting template '{template_name}': {e}")
            return None

    # Header methods
    async def get_header(self, header_name: str) -> Optional[str]:
        """
        Get a header by name.

        Args:
            header_name: Name of the header

        Returns:
            Header content if found, None otherwise
        """
        header = await self.header_repository.get_by_name(header_name)
        if header:
            return header.content
        self.logger.warning(f"Header '{header_name}' not found")
        return None

    async def format_header(self, header_name: str, **kwargs) -> Optional[str]:
        """
        Format a header with the given parameters.

        Args:
            header_name: Name of the header
            **kwargs: Parameters to format the header with

        Returns:
            Formatted header if successful, None otherwise
        """
        try:
            header = await self.header_repository.get_by_name(header_name)
            if not header:
                self.logger.warning(f"Header '{header_name}' not found")
                return None

            return header.content.format(**kwargs)
        except KeyError as e:
            self.logger.error(f"KeyError in header '{header_name}': {e}")
            return None
        except ValueError as e:
            self.logger.error(f"ValueError in header '{header_name}': {e}")
            return None

    async def get_all_headers_by_category(self, category: str) -> List[Dict[str, str]]:
        """
        Get all headers for a specific category.

        Args:
            category: Category of headers to get

        Returns:
            List of dictionaries with name and content
        """
        headers = await self.header_repository.get_all_by_category(category)
        return [{"name": h.name, "content": h.content} for h in headers]

    async def get_all_header_names_by_category(self, category: str) -> List[str]:
        """
        Get all header names for a specific category.

        Args:
            category: Category of headers to get

        Returns:
            List of header names
        """
        headers = await self.header_repository.get_all_by_category(category)
        return [header.name for header in headers]

    # Preamble methods
    async def get_default_preamble(
        self, preamble_type: str = "resume_preamble"
    ) -> Optional[str]:
        """
        Get the default preamble for a specific type.

        Args:
            preamble_type: Type of preamble (default: resume_preamble)

        Returns:
            Default preamble content if found, None otherwise
        """
        preamble = await self.preamble_repository.get_default(preamble_type)
        if preamble:
            return preamble.content
        self.logger.warning(f"Default preamble for type '{preamble_type}' not found")
        return None

    async def get_preamble(
        self, name: str, preamble_type: str = "resume_preamble"
    ) -> Optional[str]:
        """
        Get a preamble by name and type.

        Args:
            name: Name of the preamble
            preamble_type: Type of preamble (default: resume_preamble)

        Returns:
            Preamble content if found, None otherwise
        """
        preamble = await self.preamble_repository.get_by_name(name, preamble_type)
        if preamble:
            return preamble.content
        self.logger.warning(f"Preamble '{name}' of type '{preamble_type}' not found")
        return None

    # Cache management
    def clear_caches(self) -> None:
        """Clear all repository caches."""
        self.header_repository.clear_cache()
        self.template_repository.clear_cache()
        self.preamble_repository.clear_cache()
        self.logger.debug("All TeX caches cleared")
