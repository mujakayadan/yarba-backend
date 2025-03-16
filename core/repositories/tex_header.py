"""TeX header repository implementation."""

from datetime import datetime
from typing import List, Optional

from ..models.tex_header import TexHeader
from .base import BeanieRepository


class TexHeaderRepository(BeanieRepository[TexHeader]):
    """Repository for TeX headers."""

    def __init__(self):
        """Initialize the repository."""
        super().__init__(TexHeader)

    async def get_by_name(
        self, name: str, category: str = "resume_section"
    ) -> Optional[TexHeader]:
        """
        Get a TeX header by name and category.

        Args:
            name: Name of the TeX header
            category: Category of the TeX header (default: resume_section)

        Returns:
            The TeX header if found, None otherwise
        """
        return await TexHeader.find_one({"name": name, "category": category})

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
        return await TexHeader.find_one(
            {"name": name, "category": category, "is_default": True}
        )

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
        return await TexHeader.find({"category": category}).to_list()

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
        return header
