"""Base service abstraction for common business logic patterns."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.models import Entity, EntityID
from leadr.common.repositories import BaseRepository

# Type variables for generic service
DomainEntityT = TypeVar("DomainEntityT", bound=Entity)
RepositoryT = TypeVar("RepositoryT", bound=BaseRepository)


class BaseService(ABC, Generic[DomainEntityT, RepositoryT]):
    """Abstract base service providing common business logic patterns.

    All services should extend this class to ensure consistent patterns for:
    - Repository initialization
    - Standard CRUD operations
    - Error handling with domain exceptions

    The service layer sits between API routes and repositories, providing:
    - Business logic orchestration
    - Domain validation
    - Transaction boundaries
    - Consistent error handling
    """

    def __init__(self, session: AsyncSession):
        """Initialize service with database session.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.repository = self._create_repository(session)

    @abstractmethod
    def _create_repository(self, session: AsyncSession) -> RepositoryT:
        """Create the repository instance for this service.

        Args:
            session: SQLAlchemy async session

        Returns:
            Repository instance

        Example:
            def _create_repository(self, session: AsyncSession) -> AccountRepository:
                return AccountRepository(session)
        """

    @abstractmethod
    def _get_entity_name(self) -> str:
        """Get the entity type name for error messages.

        Returns:
            Entity type name (e.g., "Account", "APIKey")

        Example:
            def _get_entity_name(self) -> str:
                return "Account"
        """

    async def get_by_id(self, entity_id: EntityID) -> DomainEntityT | None:
        """Get an entity by its ID.

        Args:
            entity_id: The ID of the entity to retrieve

        Returns:
            The domain entity if found, None otherwise
        """
        return await self.repository.get_by_id(entity_id)

    async def get_by_id_or_raise(self, entity_id: EntityID) -> DomainEntityT:
        """Get an entity by its ID or raise EntityNotFoundError.

        Args:
            entity_id: The ID of the entity to retrieve

        Returns:
            The domain entity

        Raises:
            EntityNotFoundError: If the entity is not found
                (converted to HTTP 404 by global handler)
        """
        entity = await self.repository.get_by_id(entity_id)
        if not entity:
            raise EntityNotFoundError(self._get_entity_name(), str(entity_id))
        return entity

    async def delete(self, entity_id: EntityID) -> None:
        """Soft-delete an entity.

        Args:
            entity_id: The ID of the entity to delete

        Raises:
            EntityNotFoundError: If the entity doesn't exist
        """
        # Verify entity exists before deleting
        await self.get_by_id_or_raise(entity_id)
        await self.repository.delete(entity_id)

    async def soft_delete(self, entity_id: EntityID) -> DomainEntityT:
        """Soft-delete an entity and return it before deletion.

        Useful for endpoints that need to return the deleted entity in the response.

        Args:
            entity_id: The ID of the entity to delete

        Returns:
            The entity before it was deleted

        Raises:
            EntityNotFoundError: If the entity doesn't exist
        """
        entity = await self.get_by_id_or_raise(entity_id)
        await self.repository.delete(entity_id)
        return entity

    async def list_all(self) -> list[DomainEntityT]:
        """List all non-deleted entities.

        Returns:
            List of domain entities
        """
        return await self.repository.list_all()
