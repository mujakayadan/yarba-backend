"""Preamble repository implementation."""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from config.logging_config import get_logger

from ..models.preamble import Preamble
from .base_repository import BeanieRepository


class PreambleRepository(BeanieRepository[Preamble]):
    """Repository for LaTeX preambles."""

    def __init__(self):
        """Initialize the repository."""
        super().__init__(Preamble)
        self.logger = get_logger(__name__)

    async def get_by_name(
        self, name: str, preamble_type: str = "resume_preamble"
    ) -> Optional[Preamble]:
        """
        Get a preamble by name and type.

        Args:
            name: Name of the preamble
            preamble_type: Type of preamble (default: resume_preamble)

        Returns:
            Preamble if found, None otherwise
        """
        return await Preamble.find_one({"name": name, "type": preamble_type})

    async def get_by_type(
        self, preamble_type: str = "resume_preamble"
    ) -> List[Preamble]:
        """
        Get all preambles of a specific type.

        Args:
            preamble_type: Type of preambles to get (default: resume_preamble)

        Returns:
            List of preambles
        """
        return await Preamble.find({"type": preamble_type}).to_list()

    async def get_default(
        self, preamble_type: str = "resume_preamble"
    ) -> Optional[Preamble]:
        """
        Get the default preamble for a specific type.

        Args:
            preamble_type: Type of preamble to get the default for (default: resume_preamble)

        Returns:
            The default preamble if found, None otherwise
        """
        return await Preamble.find_one({"type": preamble_type, "is_default": True})

    async def set_as_default(self, preamble_id: str) -> bool:
        """
        Set a preamble as the default for its type.

        Args:
            preamble_id: ID of the preamble to set as default

        Returns:
            bool: True if successful, False otherwise
        """
        preamble = await Preamble.get(preamble_id)
        if not preamble:
            return False

        # Remove default flag from other preambles of the same type
        await Preamble.find({"type": preamble.type, "is_default": True}).update(
            {"$set": {"is_default": False, "updated_at": datetime.now(timezone.utc)}}
        )

        # Set this preamble as default
        preamble.is_default = True
        preamble.updated_at = datetime.now(timezone.utc)
        await preamble.save()
        return True

    async def create_preamble(
        self,
        name: str,
        content: str,
        preamble_type: str = "resume_preamble",
        is_default: bool = False,
    ) -> Preamble:
        """
        Create a new preamble.

        Args:
            name: Name of the preamble
            content: LaTeX code content
            preamble_type: Type of preamble (default: resume_preamble)
            is_default: Whether this is a default preamble (default: False)

        Returns:
            Created preamble
        """
        if is_default:
            # Remove default flag from other preambles of the same type
            await Preamble.find({"type": preamble_type, "is_default": True}).update(
                {
                    "$set": {
                        "is_default": False,
                        "updated_at": datetime.now(timezone.utc),
                    }
                }
            )

        preamble = Preamble(
            name=name,
            content=content,
            type=preamble_type,
            is_default=is_default,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await preamble.create()
        return preamble

    async def update_content(
        self, preamble_id: str, content: str, set_as_default: bool = False
    ) -> Optional[Preamble]:
        """
        Update the content of a preamble.

        Args:
            preamble_id: ID of the preamble to update
            content: New LaTeX code content
            set_as_default: Whether to set this preamble as default (default: False)

        Returns:
            Updated preamble if found, None otherwise
        """
        preamble = await Preamble.get(preamble_id)
        if not preamble:
            return None

        if set_as_default:
            # Remove default flag from other preambles of the same type
            await Preamble.find({"type": preamble.type, "is_default": True}).update(
                {
                    "$set": {
                        "is_default": False,
                        "updated_at": datetime.now(timezone.utc),
                    }
                }
            )
            preamble.is_default = True

        preamble.content = content
        preamble.updated_at = datetime.now(timezone.utc)
        await preamble.save()
        return preamble

    async def clear_cache(self) -> None:
        """Clear the header cache."""
        self.logger.debug("Preamble cache cleared")


async def get_preamble_repository(self) -> PreambleRepository:
    """
    Get the preamble repository.
    """
    return PreambleRepository()
