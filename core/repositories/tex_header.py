"""TeX header repository implementation."""

from typing import List, Optional

from ..models.tex_header import TexHeader
from .base import BeanieRepository


class TexHeaderRepository(BeanieRepository[TexHeader]):
    """Repository for TeX headers."""

    def __init__(self):
        """Initialize the repository."""
        super().__init__(TexHeader)

    async def get_by_name(
        self, name: str, category: str = "resume"
    ) -> Optional[TexHeader]:
        """
        Get a TeX header by name and category.

        Args:
            name: Name of the TeX header
            category: Category of the TeX header

        Returns:
            The TeX header if found, None otherwise
        """
        return await TexHeader.get_by_name(name, category)

    async def get_default(
        self, name: str, category: str = "resume"
    ) -> Optional[TexHeader]:
        """
        Get the default TeX header for a specific name and category.

        Args:
            name: Name of the TeX header
            category: Category of the TeX header

        Returns:
            The default TeX header if found, None otherwise
        """
        return await TexHeader.get_default(name, category)

    async def get_all_by_category(self, category: str = "resume") -> List[TexHeader]:
        """
        Get all TeX headers for a specific category.

        Args:
            category: Category of the TeX headers

        Returns:
            List of TeX headers
        """
        return await TexHeader.find({"category": category}).to_list()
