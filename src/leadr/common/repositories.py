"""Base repository abstraction for common CRUD operations."""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import UUID4
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.common.domain.cursor import Cursor
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import PrefixedID
from leadr.common.domain.models import Entity
from leadr.common.domain.pagination import (
    CursorPosition,
    PaginationDirection,
    SortDirection,
    SortField,
)
from leadr.common.domain.pagination_result import PaginatedResult
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

    @staticmethod
    def _extract_uuid(id_value: UUID | PrefixedID | UUID4 | str) -> UUID:
        """Extract UUID from various ID types.

        Handles conversion from PrefixedID to UUID for database operations.

        Args:
            id_value: ID value that can be UUID, PrefixedID, UUID4, or string

        Returns:
            UUID instance for database querying
        """
        if isinstance(id_value, PrefixedID):
            return id_value.uuid
        if isinstance(id_value, UUID):
            return id_value
        return UUID(str(id_value))

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
        self, entity_id: UUID4 | PrefixedID, include_deleted: bool = False
    ) -> DomainEntityT | None:
        """Get an entity by its ID.

        Args:
            entity_id: Entity ID to retrieve
            include_deleted: If True, include soft-deleted entities. Defaults to False.

        Returns:
            Domain entity if found, None otherwise
        """
        orm_class = self._get_orm_class()
        query = select(orm_class).where(orm_class.id == self._extract_uuid(entity_id))

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
        entity_uuid = self._extract_uuid(entity.id)
        result = await self.session.execute(select(orm_class).where(orm_class.id == entity_uuid))
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

    async def delete(self, entity_id: UUID4 | PrefixedID) -> None:
        """Soft delete an entity by setting its deleted_at timestamp.

        Args:
            entity_id: ID of entity to delete

        Raises:
            EntityNotFoundError: If entity is not found
        """
        orm_class = self._get_orm_class()
        entity_uuid = self._extract_uuid(entity_id)

        # Verify entity exists
        result = await self.session.execute(select(orm_class).where(orm_class.id == entity_uuid))
        orm = result.scalar_one_or_none()

        if not orm:
            # Get entity type name from ORM class
            entity_type = orm_class.__name__.replace("ORM", "")
            raise EntityNotFoundError(entity_type, str(entity_id))

        # Perform soft delete
        await self.session.execute(
            update(orm_class)
            .where(orm_class.id == entity_uuid)
            .values(deleted_at=datetime.now(UTC))
        )
        await self.session.commit()

    @abstractmethod
    async def filter(
        self, account_id: UUID4 | PrefixedID | None = None, **kwargs: Any
    ) -> list[DomainEntityT]:
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
        account_uuid = self._extract_uuid(account_id)
        query = select(orm_class).where(
            orm_class.account_id == account_uuid,  # type: ignore[attr-defined]
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

    # Pagination support methods

    def _get_orm_column(self, field_name: str) -> Any:
        """Get ORM column by field name.

        Args:
            field_name: Name of the field

        Returns:
            SQLAlchemy column object

        Raises:
            ValueError: If field doesn't exist on ORM model
        """
        orm_class = self._get_orm_class()
        if not hasattr(orm_class, field_name):
            raise ValueError(f"Unknown sort field: {field_name}")
        return getattr(orm_class, field_name)

    def _convert_cursor_value(self, value: Any, column: Any) -> Any:
        """Convert cursor value to match ORM column type.

        Cursor values are stored as JSON primitives. This method converts them back
        to the Python types expected by SQLAlchemy for proper SQL comparisons.

        Args:
            value: Cursor value (JSON primitive: str, int, float, bool, None)
            column: SQLAlchemy column object

        Returns:
            Value converted to match column's Python type
        """
        from datetime import datetime
        from uuid import UUID

        from sqlalchemy import DateTime, Uuid

        # Get the column type
        column_type = column.type

        # Convert based on column type
        if isinstance(column_type, DateTime) and isinstance(value, str):
            # Convert ISO format string to datetime
            return datetime.fromisoformat(value)
        elif isinstance(column_type, Uuid) and isinstance(value, str):
            # Convert string to UUID
            return UUID(value)
        else:
            # Keep as-is for other types (int, float, str, bool, None)
            return value

    def _build_cursor_where_clause(
        self,
        cursor: Cursor,
        sort_fields: list[SortField],
    ) -> Any:
        """Build WHERE clause for cursor-based pagination.

        Generates complex WHERE conditions for compound sorts with mixed ASC/DESC.

        For example, with cursor at (score=100, created_at='2025-01-01', id=42)
        and sort spec (score DESC, created_at ASC, id ASC):

        Forward: WHERE score < 100
                OR (score = 100 AND created_at > '2025-01-01')
                OR (score = 100 AND created_at = '2025-01-01' AND id > 42)

        Backward: WHERE score > 100
                 OR (score = 100 AND created_at < '2025-01-01')
                 OR (score = 100 AND created_at = '2025-01-01' AND id < 42)

        Args:
            cursor: Cursor containing position and sort information
            sort_fields: List of sort fields

        Returns:
            SQLAlchemy WHERE clause condition
        """
        position_values = cursor.position.values
        is_backward = cursor.direction == PaginationDirection.BACKWARD

        # Build OR conditions for each level of the compound sort
        or_conditions = []

        for i, sort_field in enumerate(sort_fields):
            # Get the comparison operator for this field
            # For forward pagination: DESC uses <, ASC uses >
            # For backward pagination: DESC uses >, ASC uses <
            if is_backward:
                # Backward: flip the operators
                comp_op = "__gt__" if sort_field.direction == SortDirection.DESC else "__lt__"
            else:
                # Forward: normal operators
                comp_op = "__lt__" if sort_field.direction == SortDirection.DESC else "__gt__"

            # Build equality conditions for all previous fields
            equality_conditions = []
            for j in range(i):
                prev_field = sort_fields[j]
                prev_column = self._get_orm_column(prev_field.name)
                prev_value = self._convert_cursor_value(position_values[j], prev_column)
                equality_conditions.append(prev_column == prev_value)

            # Add comparison condition for current field
            current_column = self._get_orm_column(sort_field.name)
            current_value = self._convert_cursor_value(position_values[i], current_column)
            comparison = getattr(current_column, comp_op)(current_value)

            # Combine: all previous equals AND current comparison
            if equality_conditions:
                or_conditions.append(and_(*equality_conditions, comparison))
            else:
                or_conditions.append(comparison)

        return or_(*or_conditions)

    def _apply_sort(self, query: Any, sort_fields: list[SortField]) -> Any:
        """Apply sorting to a query.

        Args:
            query: SQLAlchemy query to sort
            sort_fields: List of sort fields

        Returns:
            Query with sorting applied
        """
        for sort_field in sort_fields:
            column = self._get_orm_column(sort_field.name)
            if sort_field.direction == SortDirection.DESC:
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())
        return query

    def _extract_cursor_position(
        self,
        orm: ORMModelT,
        sort_fields: list[SortField],
    ) -> CursorPosition:
        """Extract cursor position from an ORM model.

        Args:
            orm: ORM model instance
            sort_fields: List of sort fields to extract values for

        Returns:
            CursorPosition with values for each sort field
        """
        values = []
        for sort_field in sort_fields:
            value = getattr(orm, sort_field.name)
            values.append(value)

        entity_id = str(orm.id)
        return CursorPosition(values=tuple(values), entity_id=entity_id)

    async def _execute_paginated_query(
        self,
        query: Any,
        sort_fields: list[SortField],
        cursor: Cursor | None,
        limit: int,
    ) -> PaginatedResult[DomainEntityT]:
        """Execute a paginated query and return results with metadata.

        Fetches limit+1 records to determine has_next efficiently.

        Args:
            query: Base SQLAlchemy query (with filters applied)
            sort_fields: List of sort fields
            cursor: Optional cursor for pagination
            limit: Number of items to return

        Returns:
            PaginatedResult with items and pagination metadata
        """
        # Apply cursor WHERE clause if present
        if cursor is not None:
            cursor_where = self._build_cursor_where_clause(cursor, sort_fields)
            query = query.where(cursor_where)

        # Apply sorting
        query = self._apply_sort(query, sort_fields)

        # Fetch limit+1 to detect has_next
        query = query.limit(limit + 1)

        # Execute query
        result = await self.session.execute(query)
        orms = list(result.scalars().all())

        # Determine if there are more results
        has_more = len(orms) > limit

        # Trim to limit
        if has_more:
            orms = orms[:limit]

        # Convert to domain entities
        items = [self._to_domain(orm) for orm in orms]

        # Determine pagination metadata
        if cursor is not None and cursor.direction == PaginationDirection.BACKWARD:
            # For backward pagination, we have has_prev if there are more results
            has_next = True  # We came from ahead, so there's always a next
            has_prev = has_more
            next_position = self._extract_cursor_position(orms[-1], sort_fields) if orms else None
            prev_position = (
                self._extract_cursor_position(orms[0], sort_fields) if orms and has_prev else None
            )
        else:
            # For forward pagination (or no cursor)
            has_next = has_more
            has_prev = cursor is not None  # If we have a cursor, we can go back
            next_position = (
                self._extract_cursor_position(orms[-1], sort_fields) if orms and has_next else None
            )
            prev_position = (
                self._extract_cursor_position(orms[0], sort_fields) if orms and has_prev else None
            )

        return PaginatedResult(
            items=items,
            has_next=has_next,
            has_prev=has_prev,
            next_position=next_position,
            prev_position=prev_position,
        )
