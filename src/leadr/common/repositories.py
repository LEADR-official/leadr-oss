"""Base repository abstraction for common CRUD operations."""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import UUID4
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.models import Entity
from leadr.common.orm import Base

# Type variables for generic repository
DomainEntityT = TypeVar("DomainEntityT", bound=Entity)
ORMModelT = TypeVar("ORMModelT", bound=Base)


class BaseRepository(ABC, Generic[DomainEntityT, ORMModelT]):
    """Abstract base repository providing common CRUD operations.

    All repositories should extend this class and implement the abstract methods
    for converting between domain entities and ORM models.

    All delete operations are soft deletes by default, setting deleted_at timestamp.
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    @abstractmethod
    def _to_domain(self, orm: ORMModelT) -> DomainEntityT:
        """Convert ORM model to domain entity.

        Args:
            orm: ORM model instance

        Returns:
            Domain entity instance
        """

    @abstractmethod
    def _to_orm(self, entity: DomainEntityT) -> ORMModelT:
        """Convert domain entity to ORM model.

        Args:
            entity: Domain entity instance

        Returns:
            ORM model instance
        """

    @abstractmethod
    def _get_orm_class(self) -> type[ORMModelT]:
        """Get the ORM model class for this repository.

        Returns:
            ORM model class
        """

    async def create(self, entity: DomainEntityT) -> DomainEntityT:
        """Create a new entity in the database.

        Args:
            entity: Domain entity to create

        Returns:
            Created domain entity with refreshed data
        """
        orm = self._to_orm(entity)
        self.session.add(orm)
        await self.session.commit()
        await self.session.refresh(orm)
        return self._to_domain(orm)

    async def get_by_id(
        self, entity_id: UUID4, include_deleted: bool = False
    ) -> DomainEntityT | None:
        """Get an entity by its ID.

        Args:
            entity_id: Entity ID to retrieve
            include_deleted: If True, include soft-deleted entities. Defaults to False.

        Returns:
            Domain entity if found, None otherwise
        """
        orm_class = self._get_orm_class()
        query = select(orm_class).where(orm_class.id == UUID(str(entity_id)))

        if not include_deleted:
            query = query.where(orm_class.deleted_at.is_(None))

        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()

        return self._to_domain(orm) if orm else None

    async def update(self, entity: DomainEntityT) -> DomainEntityT:
        """Update an existing entity in the database.

        Args:
            entity: Domain entity with updated data

        Returns:
            Updated domain entity with refreshed data

        Raises:
            EntityNotFoundError: If entity is not found
        """
        orm_class = self._get_orm_class()
        result = await self.session.execute(
            select(orm_class).where(orm_class.id == UUID(str(entity.id)))
        )
        orm = result.scalar_one_or_none()

        if not orm:
            # Get entity type name from ORM class
            entity_type = orm_class.__name__.replace("ORM", "")
            raise EntityNotFoundError(entity_type, str(entity.id))

        # Update ORM from entity
        updated_orm = self._to_orm(entity)
        for key, value in updated_orm.__dict__.items():
            if not key.startswith("_"):
                setattr(orm, key, value)

        await self.session.commit()
        await self.session.refresh(orm)
        return self._to_domain(orm)

    async def delete(self, entity_id: UUID4) -> None:
        """Soft delete an entity by setting its deleted_at timestamp.

        Args:
            entity_id: ID of entity to delete

        Raises:
            EntityNotFoundError: If entity is not found
        """
        orm_class = self._get_orm_class()

        # Verify entity exists
        result = await self.session.execute(
            select(orm_class).where(orm_class.id == UUID(str(entity_id)))
        )
        orm = result.scalar_one_or_none()

        if not orm:
            # Get entity type name from ORM class
            entity_type = orm_class.__name__.replace("ORM", "")
            raise EntityNotFoundError(entity_type, str(entity_id))

        # Perform soft delete
        await self.session.execute(
            update(orm_class)
            .where(orm_class.id == UUID(str(entity_id)))
            .values(deleted_at=datetime.now(UTC))
        )
        await self.session.commit()

    @abstractmethod
    async def filter(self, account_id: UUID4, **kwargs: Any) -> list[DomainEntityT]:
        """Filter entities based on criteria.

        For multi-tenant entities, implementations MUST override this to make
        account_id required (no default). For top-level entities like Account,
        account_id can remain optional and unused.

        Args:
            account_id: Optional account ID for filtering. Multi-tenant entities
                       MUST override to make this required (account_id: UUID).
            **kwargs: Additional filter parameters specific to the entity type.

        Returns:
            List of domain entities matching the filter criteria

        Example (multi-tenant - account_id required):
            async def filter(
                self,
                account_id: UUID,  # Required, no default
                status: str | None = None,
                **kwargs
            ) -> list[User]:
                # Implementation with account_id required

        Example (top-level tenant - account_id optional/unused):
            async def filter(
                self,
                account_id: UUID | None = None,  # Optional, unused
                status: str | None = None,
                **kwargs
            ) -> list[Account]:
                # Implementation where account_id is not used
        """

    async def _list_all_unfiltered(self, include_deleted: bool = False) -> list[DomainEntityT]:
        """List all entities without filtering by account.

        PRIVATE METHOD - Use filter() in application code for multi-tenant safety.
        This method is for internal use and testing only.

        Args:
            include_deleted: If True, include soft-deleted entities. Defaults to False.

        Returns:
            List of domain entities
        """
        orm_class = self._get_orm_class()
        query = select(orm_class)

        if not include_deleted:
            query = query.where(orm_class.deleted_at.is_(None))

        result = await self.session.execute(query)
        orms = result.scalars().all()

        return [self._to_domain(orm) for orm in orms]

    # Helper methods for common repository patterns

    async def _get_by_field(self, field_name: str, value: Any) -> DomainEntityT | None:
        """Get an entity by a specific field value.

        This is a helper method that reduces boilerplate for get_by_<field> patterns
        like get_by_slug, get_by_email, get_by_prefix, etc.

        Args:
            field_name: Name of the ORM field to query
            value: Value to match

        Returns:
            Domain entity if found, None otherwise

        Example:
            async def get_by_slug(self, slug: str) -> Account | None:
                return await self._get_by_field("slug", slug)
        """
        orm_class = self._get_orm_class()
        field = getattr(orm_class, field_name)
        query = select(orm_class).where(field == value, orm_class.deleted_at.is_(None))
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def _list_by_account(
        self,
        account_id: UUID4,
        additional_filters: list[Any] | None = None,
    ) -> list[DomainEntityT]:
        """List entities for a specific account.

        This is a helper method that reduces boilerplate for list_by_account patterns.

        Args:
            account_id: Account ID to filter by
            additional_filters: Optional list of additional SQLAlchemy filter expressions

        Returns:
            List of domain entities belonging to the account

        Example:
            async def list_by_account(self, account_id: UUID, active_only: bool = False):
                filters = []
                if active_only:
                    filters.append(UserORM.status == UserStatusEnum.ACTIVE)
                return await self._list_by_account(account_id, filters)
        """
        orm_class = self._get_orm_class()
        query = select(orm_class).where(
            orm_class.account_id == account_id,  # type: ignore[attr-defined]
            orm_class.deleted_at.is_(None),
        )

        if additional_filters:
            for filter_expr in additional_filters:
                query = query.where(filter_expr)

        result = await self.session.execute(query)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]

    async def _count_where(self, *conditions: Any) -> int:
        """Count entities matching given conditions.

        This is a helper method that reduces boilerplate for count operations.

        Args:
            *conditions: SQLAlchemy filter expressions to apply

        Returns:
            Count of entities matching the conditions

        Example:
            async def count_active_by_account(self, account_id: UUID) -> int:
                return await self._count_where(
                    APIKeyORM.account_id == account_id,
                    APIKeyORM.status == APIKeyStatusEnum.ACTIVE,
                    APIKeyORM.deleted_at.is_(None),
                )
        """
        orm_class = self._get_orm_class()
        query = select(func.count()).select_from(orm_class)

        for condition in conditions:
            query = query.where(condition)

        result = await self.session.execute(query)
        return result.scalar_one()
