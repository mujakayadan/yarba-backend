"""TeX header repository implementation."""

from datetime import datetime
from typing import Dict, List, Optional

from ..models.tex_header import TexHeader
from .base import BeanieRepository


class TexHeaderRepository(BeanieRepository[TexHeader]):
    """Repository for TeX headers with caching support."""

    def __init__(self):
        """Initialize the repository."""
        super().__init__(TexHeader)
        self._cached_headers: Dict[str, TexHeader] = {}
        self.logger = self._get_logger()

    async def get_by_name(
        self, name: str, category: str = "resume_section"
    ) -> Optional[TexHeader]:
        """
        Get a TeX header by name and category with caching.

        Args:
            name: Name of the TeX header
            category: Category of the TeX header (default: resume_section)

        Returns:
            The TeX header if found, None otherwise
        """
        cache_key = f"{name}:{category}"
        try:
            # Use cached header if available
            if cache_key in self._cached_headers:
                return self._cached_headers[cache_key]

            # Find header in database
            header = await TexHeader.find_one({"name": name, "category": category})
            if header:
                # Cache the header for future use
                self._cached_headers[cache_key] = header
                return header

            self.logger.warning(f"Header '{name}' in category '{category}' not found")
            return None
        except Exception as e:
            self.logger.error(f"Error retrieving header '{name}': {str(e)}")
            return None

    async def get_default(
        self, name: str, category: str = "resume_section"
    ) -> Optional[TexHeader]:
        """
        Get the default TeX header for a specific name and category.

        Args:
            name: Name of the TeX header
            category: Category of the TeX header (default: resume_section)

        Returns:
            The default TeX header if found, None otherwise
        """
        header = await TexHeader.find_one(
            {"name": name, "category": category, "is_default": True}
        )

        if header:
            cache_key = f"{name}:{category}"
            self._cached_headers[cache_key] = header

        return header

    async def get_all_by_category(
        self, category: str = "resume_section"
    ) -> List[TexHeader]:
        """
        Get all TeX headers for a specific category.

        Args:
            category: Category of the TeX headers (default: resume_section)

        Returns:
            List of TeX headers
        """
        headers = await TexHeader.find({"category": category}).to_list()

        # Cache all headers by their name:category
        for header in headers:
            self._cached_headers[f"{header.name}:{category}"] = header

        return headers

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
            The created TeX header
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

        # Cache the new header
        self._cached_headers[f"{name}:{category}"] = header

        return header

    async def update_content(self, header_id: str, content: str) -> Optional[TexHeader]:
        """
        Update the content of a TeX header.

        Args:
            header_id: ID of the header to update
            content: New LaTeX code content

        Returns:
            Updated TeX header if found, None otherwise
        """
        header = await TexHeader.get(header_id)
        if not header:
            return None

        header.content = content
        header.updated_at = datetime.utcnow()
        await header.save()

        # Update cache if header is in cache
        cache_key = f"{header.name}:{header.category}"
        if cache_key in self._cached_headers:
            self._cached_headers[cache_key] = header

        return header

    def clear_cache(self) -> None:
        """Clear the header cache."""
        self._cached_headers.clear()
        self.logger.debug("Header cache cleared")
