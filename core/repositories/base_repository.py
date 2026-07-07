"""Base repository interfaces for the application."""

from abc import ABC, abstractmethod
from typing import TypeVar

from beanie import Document, PydanticObjectId
from pydantic import BaseModel

from ..utils.object_id import ObjectIdLike, coerce_object_id

T = TypeVar("T", bound=Document)
M = TypeVar("M", bound=BaseModel)


class BaseRepository[T: Document](ABC):
    """Base repository interface for database operations."""

    @abstractmethod
    async def get_by_id(self, id: ObjectIdLike) -> T | None:
        """Get a document by ID.

        Args:
            id: Document ID

        Returns:
            Optional[T]: Document if found, None otherwise
        """

    @abstractmethod
    async def get_all(self) -> list[T]:
        """Get all documents.

        Returns:
            List[T]: List of documents
        """

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create a new document.

        Args:
            entity: Document to create

        Returns:
            T: Created document
        """

    @abstractmethod
    async def update(self, id: PydanticObjectId, entity: T) -> T | None:
        """Update a document.

        Args:
            id: Document ID
            entity: Updated document

        Returns:
            Optional[T]: Updated document if successful, None otherwise
        """

    @abstractmethod
    async def delete(self, id: PydanticObjectId) -> bool:
        """Delete a document.

        Args:
            id: Document ID

        Returns:
            bool: True if successful, False otherwise
        """


class BeanieRepository(BaseRepository[T]):
    """Base repository implementation using Beanie ODM."""

    def __init__(self, model_class: type[T]):
        """Initialize the repository.

        Args:
            model_class: Document model class
        """
        self.model_class = model_class

    async def get_by_id(self, id: ObjectIdLike) -> T | None:
        """Get a document by ID.

        Args:
            id: Document ID

        Returns:
            Optional[T]: Document if found, None otherwise
        """
        return await self.model_class.get(coerce_object_id(id))

    async def get_all(self) -> list[T]:
        """Get all documents.

        Returns:
            List[T]: List of documents
        """
        return await self.model_class.find_all().to_list()

    async def create(self, entity: T) -> T:
        """Create a new document.

        Args:
            entity: Document to create

        Returns:
            T: Created document
        """
        await entity.insert()
        return entity

    async def update(self, id: PydanticObjectId, entity: T) -> T | None:
        """Update a document.

        Args:
            id: Document ID
            entity: Updated document

        Returns:
            Optional[T]: Updated document if successful, None otherwise
        """
        existing = await self.get_by_id(id)
        if not existing:
            return None

        await entity.replace()
        return entity

    async def delete(self, id: PydanticObjectId) -> bool:
        """Delete a document.

        Args:
            id: Document ID

        Returns:
            bool: True if successful, False otherwise
        """
        entity = await self.get_by_id(id)
        if not entity:
            return False

        await entity.delete()
        return True
