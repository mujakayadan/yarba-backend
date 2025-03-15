"""Preamble repository implementation."""

from typing import List, Optional

from ..models.preamble import Preamble
from .base import BeanieRepository


class PreambleRepository(BeanieRepository[Preamble]):
    """Repository for LaTeX preambles."""

    def __init__(self):
        """Initialize the repository."""
        super().__init__(Preamble)

    async def get_by_type(self, preamble_type: str) -> List[Preamble]:
        """
        Get all preambles of a specific type.

        Args:
            preamble_type: Type of preambles to get

        Returns:
            List of preambles
        """
        return await Preamble.find({"type": preamble_type}).to_list()

    async def get_default(self, preamble_type: str) -> Optional[Preamble]:
        """
        Get the default preamble for a specific type.

        Args:
            preamble_type: Type of preamble to get the default for

        Returns:
            The default preamble if found, None otherwise
        """
        return await Preamble.get_default(preamble_type)
