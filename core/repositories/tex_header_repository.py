"""TeX header repository implementation with support for different component types."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from core.models.tex_header import TexHeader
from core.repositories.base_repository import BeanieRepository


class TexHeaderRepository(BeanieRepository[TexHeader]):
    """Repository for TeX headers with caching support and component type handling."""

    def __init__(self):
        """Initialize the repository."""
        super().__init__(TexHeader)
        self._cached_headers: Dict[str, TexHeader] = {}
        self.logger = self._get_logger()

    async def get_by_name(self, name: str) -> Optional[TexHeader]:
        """
        Get a header by name with caching.

        Args:
            name: Name of the header

        Returns:
            TexHeader if found, None otherwise
        """
        try:
            # Use cached header if available
            if name in self._cached_headers:
                return self._cached_headers[name]

            # Find header in database
            header = await TexHeader.find_one(TexHeader.name == name)
            if header:
                # Cache the header for future use
                self._cached_headers[name] = header
                return header

            self.logger.warning(f"Header '{name}' not found in the database")
            return None

        except Exception as e:
            self.logger.error(f"Error retrieving header '{name}': {str(e)}")
            return None

    async def get_all_by_category(self, category: str) -> List[TexHeader]:
        """
        Get all headers of a specific category.

        Args:
            category: Category of headers to get (e.g., resume_section, template, preamble)

        Returns:
            List of headers
        """
        return await TexHeader.find(TexHeader.category == category).to_list()

    async def get_default(
        self, category: str = "resume_section"
    ) -> Optional[TexHeader]:
        """
        Get the default header for a specific category.

        Args:
            category: Category of header to get the default for

        Returns:
            The default header if found, None otherwise
        """
        header = await TexHeader.find_one({"category": category, "is_default": True})
        if header:
            self._cached_headers[header.name] = header
        return header

    async def get_template(self, name: str) -> Optional[TexHeader]:
        """
        Get a template (special category of header) by name.

        Args:
            name: Name of the template

        Returns:
            TexHeader if found, None otherwise
        """
        try:
            # Just get by name but log appropriately for templates
            template = await self.get_by_name(name)
            if not template:
                self.logger.warning(f"Template '{name}' not found in the database")
            return template
        except Exception as e:
            self.logger.error(f"Error retrieving template '{name}': {str(e)}")
            return None

    async def get_preamble(self, name: str) -> Optional[TexHeader]:
        """
        Get a preamble (special category of header) by name.

        Args:
            name: Name of the preamble

        Returns:
            TexHeader if found, None otherwise
        """
        try:
            # Just get by name but log appropriately for preambles
            preamble = await self.get_by_name(name)
            if not preamble:
                self.logger.warning(f"Preamble '{name}' not found in the database")
            return preamble
        except Exception as e:
            self.logger.error(f"Error retrieving preamble '{name}': {str(e)}")
            return None

    def format_tex_content(self, header: TexHeader, **kwargs) -> str:
        """
        Safely format a header's content with the given parameters.

        Args:
            header: The header to format
            **kwargs: The parameters to format the content with

        Returns:
            str: The formatted content

        Raises:
            ValueError: If formatting fails
        """
        try:
            return header.content.format(**kwargs)
        except KeyError as e:
            self.logger.error(f"KeyError in header '{header.name}': {e}")
            raise ValueError(f"Missing key in header '{header.name}': {e}")
        except ValueError as e:
            self.logger.error(f"ValueError in header '{header.name}': {e}")
            raise ValueError(f"Error formatting header '{header.name}': {e}")

    def clear_cache(self) -> None:
        """Clear the header cache."""
        self._cached_headers.clear()
        self.logger.debug("Header cache cleared")

    async def create_header(
        self,
        name: str,
        content: str,
        category: str = "resume_section",
        is_default: bool = False,
    ) -> TexHeader:
        """
        Create a new TeX header.

        Args:
            name: Name of the header
            content: LaTeX code content
            category: Category of the header (default: resume_section)
            is_default: Whether this is a default header (default: False)

        Returns:
            Created header
        """
        header = TexHeader(
            name=name,
            content=content,
            category=category,
            is_default=is_default,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        await header.create()
        return header

    async def update_content(self, header_id: str, content: str) -> Optional[TexHeader]:
        """
        Update the content of a header.

        Args:
            header_id: ID of the header to update
            content: New LaTeX code content

        Returns:
            Updated header if found, None otherwise
        """
        header = await TexHeader.get(header_id)
        if not header:
            return None

        header.content = content
        header.updated_at = datetime.utcnow()
        await header.save()

        # Update cache if header is in cache
        if header.name in self._cached_headers:
            self._cached_headers[header.name] = header

        return header

    # Factory methods for creating specific types
    async def create_template(
        self,
        name: str,
        content: str,
        is_default: bool = False,
    ) -> TexHeader:
        """
        Create a new TeX template (special category of header).

        Args:
            name: Name of the template
            content: LaTeX code content
            is_default: Whether this is a default template (default: False)

        Returns:
            Created template
        """
        return await self.create_header(
            name=name, content=content, category="template", is_default=is_default
        )

    async def create_preamble(
        self,
        name: str,
        content: str,
        is_default: bool = False,
    ) -> TexHeader:
        """
        Create a new preamble (special category of header).

        Args:
            name: Name of the preamble
            content: LaTeX code content
            is_default: Whether this is a default preamble (default: False)

        Returns:
            Created preamble
        """
        return await self.create_header(
            name=name, content=content, category="preamble", is_default=is_default
        )


# Factory function for dependency injection
def get_tex_header_repository() -> TexHeaderRepository:
    """
    Factory function to create a TeX header repository instance.

    Returns:
        TexHeaderRepository: A new instance of the TeX header repository
    """
    return TexHeaderRepository()
