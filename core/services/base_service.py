"""Base service for application services."""

from typing import TypeVar, cast

from config.logging_config import get_logger

from ..repositories.base_repository import BaseRepository
from ..utils.object_id import coerce_object_id

T = TypeVar("T")


class BaseService[T]:
    """Base service for application services."""

    def __init__(self, repository: BaseRepository):
        """Initialize the service.

        Args:
            repository: Repository instance
        """
        self.repository = repository
        self.logger = get_logger(self.__class__.__name__)

    async def get_by_id(self, id: str) -> T | None:
        """Get an entity by ID.

        Args:
            id: Entity ID

        Returns:
            Optional[T]: Entity if found, None otherwise
        """
        self.logger.debug(f"Getting entity with ID: {id}")
        return await self.repository.get_by_id(id)

    async def get_all(self) -> list[T]:
        """Get all entities.

        Returns:
            List[T]: List of entities
        """
        self.logger.debug("Getting all entities")
        return await self.repository.get_all()

    async def create(self, entity: T) -> T:
        """Create a new entity.

        Args:
            entity: Entity to create

        Returns:
            T: Created entity
        """
        self.logger.debug(f"Creating entity: {entity}")
        return cast(T, await self.repository.create(entity))

    async def update(self, id: str, entity: T) -> T | None:
        """Update an entity.

        Args:
            id: Entity ID
            entity: Updated entity

        Returns:
            Optional[T]: Updated entity if successful, None otherwise
        """
        self.logger.debug(f"Updating entity with ID: {id}")
        return await self.repository.update(coerce_object_id(id), entity)

    async def delete(self, id: str) -> bool:
        """Delete an entity.

        Args:
            id: Entity ID

        Returns:
            bool: True if successful, False otherwise
        """
        self.logger.debug(f"Deleting entity with ID: {id}")
        return await self.repository.delete(coerce_object_id(id))
