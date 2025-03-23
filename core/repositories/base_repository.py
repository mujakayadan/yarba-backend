"""Base repository interfaces for the application."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from beanie import Document, PydanticObjectId
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from ..exceptions.base import NotFoundException

T = TypeVar("T", bound=Document)
M = TypeVar("M", bound=BaseModel)


class BaseRepository(ABC, Generic[T]):
    """Base repository interface for database operations."""

    @abstractmethod
    async def get_by_id(self, id: PydanticObjectId) -> Optional[T]:
        """
        Get a document by ID.

        Args:
            id: Document ID

        Returns:
            Optional[T]: Document if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_all(self) -> List[T]:
        """
        Get all documents.

        Returns:
            List[T]: List of documents
        """
        pass

    @abstractmethod
    async def create(self, entity: T) -> T:
        """
        Create a new document.

        Args:
            entity: Document to create

        Returns:
            T: Created document
        """
        pass

    @abstractmethod
    async def update(self, id: PydanticObjectId, entity: T) -> Optional[T]:
        """
        Update a document.

        Args:
            id: Document ID
            entity: Updated document

        Returns:
            Optional[T]: Updated document if successful, None otherwise
        """
        pass

    @abstractmethod
    async def delete(self, id: PydanticObjectId) -> bool:
        """
        Delete a document.

        Args:
            id: Document ID

        Returns:
            bool: True if successful, False otherwise
        """
        pass


class BeanieRepository(BaseRepository[T]):
    """Base repository implementation using Beanie ODM."""

    def __init__(self, model_class: Type[T]):
        """
        Initialize the repository.

        Args:
            model_class: Document model class
        """
        self.model_class = model_class

    async def get_by_id(self, id: PydanticObjectId) -> Optional[T]:
        """
        Get a document by ID.

        Args:
            id: Document ID

        Returns:
            Optional[T]: Document if found, None otherwise
        """
        return await self.model_class.get(id)

    async def get_all(self) -> List[T]:
        """
        Get all documents.

        Returns:
            List[T]: List of documents
        """
        return await self.model_class.find_all().to_list()

    async def create(self, entity: T) -> T:
        """
        Create a new document.

        Args:
            entity: Document to create

        Returns:
            T: Created document
        """
        await entity.insert()
        return entity

    async def update(self, id: PydanticObjectId, entity: T) -> Optional[T]:
        """
        Update a document.

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
        """
        Delete a document.

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


class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations.

    This class provides a base implementation for repositories with common
    CRUD operations. It is designed to be extended by specific repositories.

    Attributes:
        database: The MongoDB database instance
        collection_name: The name of the MongoDB collection
    """

    def __init__(self, database: AsyncIOMotorDatabase, collection_name: str):
        """Initialize the repository.

        Args:
            database: The MongoDB database instance
            collection_name: The name of the MongoDB collection
        """
        self.database = database
        self.collection_name = collection_name
        self.collection = database[collection_name]

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new document.

        Args:
            data: The document data

        Returns:
            Dict[str, Any]: The created document with ID
        """
        # Insert the document
        result = await self.collection.insert_one(data)

        # Get the inserted document
        document = await self.collection.find_one({"_id": result.inserted_id})

        # Convert ObjectId to string
        document["id"] = str(document.pop("_id"))

        return document

    async def find_by_id(self, id: PydanticObjectId) -> Optional[Dict[str, Any]]:
        """Find a document by ID.

        Args:
            id: The document ID

        Returns:
            Optional[Dict[str, Any]]: The document if found, None otherwise
        """
        # Find the document
        document = await self.collection.find_one({"_id": ObjectId(id)})

        # Return None if not found
        if document is None:
            return None

        # Convert ObjectId to string
        document["id"] = str(document.pop("_id"))

        return document

    async def find_all(self, **kwargs) -> List[Dict[str, Any]]:
        """Find all documents matching the criteria.

        Args:
            **kwargs: Filter criteria

        Returns:
            List[Dict[str, Any]]: List of documents
        """
        # Create filter
        filter_criteria = {}

        # Add filter criteria
        for key, value in kwargs.items():
            if value is not None:
                filter_criteria[key] = value

        # Find documents
        cursor = self.collection.find(filter_criteria)

        # Convert cursor to list
        documents = []
        async for document in cursor:
            # Convert ObjectId to string
            document["id"] = str(document.pop("_id"))
            documents.append(document)

        return documents

    async def update(
        self, id: PydanticObjectId, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a document.

        Args:
            id: The document ID
            data: The update data

        Returns:
            Dict[str, Any]: The updated document

        Raises:
            NotFoundException: If the document is not found
        """
        # Check if document exists
        document = await self.find_by_id(id)
        if document is None:
            raise NotFoundException(f"{self.collection_name.capitalize()} not found")

        # Update the document
        await self.collection.update_one({"_id": ObjectId(id)}, {"$set": data})

        # Get the updated document
        updated_document = await self.find_by_id(id)

        return updated_document

    async def delete(self, id: PydanticObjectId) -> bool:
        """Delete a document.

        Args:
            id: The document ID

        Returns:
            bool: True if deleted, False otherwise

        Raises:
            NotFoundException: If the document is not found
        """
        # Check if document exists
        document = await self.find_by_id(id)
        if document is None:
            raise NotFoundException(f"{self.collection_name.capitalize()} not found")

        # Delete the document
        result = await self.collection.delete_one({"_id": ObjectId(id)})

        return result.deleted_count > 0
