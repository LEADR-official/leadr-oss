"""Email repository for database operations."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.common.repositories import BaseRepository
from leadr.infra.email.adapters.orm import EmailORM
from leadr.infra.email.domain.models import Email


class EmailRepository(BaseRepository[Email, EmailORM]):
    """Repository for Email entities."""

    SORTABLE_FIELDS = {
        "id",
        "to",
        "status",
        "priority",
        "created_at",
        "sent_at",
        "updated_at",
    }

    def __init__(self, db: AsyncSession):
        """Initialize email repository.

        Args:
            db: Database session.
        """
        super().__init__(db)

    def _to_domain(self, orm: EmailORM) -> Email:
        """Convert ORM model to domain entity.

        Args:
            orm: ORM model instance.

        Returns:
            Domain entity.
        """
        return orm.to_domain()

    def _to_orm(self, entity: Email) -> EmailORM:
        """Convert domain entity to ORM model.

        Args:
            entity: Domain entity.

        Returns:
            ORM model instance.
        """
        return EmailORM.from_domain(entity)

    def _get_orm_class(self) -> type[EmailORM]:
        """Get the ORM class for this repository.

        Returns:
            ORM class.
        """
        return EmailORM

    async def filter(
        self,
        account_id: Any | None = None,
        *,
        pagination: PaginationParams,
        **kwargs: Any,
    ) -> PaginatedResult[Email]:
        """Filter emails by criteria with pagination.

        Args:
            account_id: Not used for emails (top-level entity).
            pagination: Pagination parameters (required).
            **kwargs: Filter parameters (to, status, etc.)

        Returns:
            Paginated result of matching Email entities.

        Raises:
            ValueError: If sort field is not in SORTABLE_FIELDS.
            CursorValidationError: If cursor is invalid or state doesn't match.
        """
        query = select(EmailORM)

        # Build filters dict for cursor validation
        filters_dict: dict[str, str] = {}

        # Apply filters based on kwargs
        if "to" in kwargs:
            query = query.where(EmailORM.to == kwargs["to"])
            filters_dict["to"] = kwargs["to"]
        if "status" in kwargs:
            query = query.where(EmailORM.status == kwargs["status"])
            filters_dict["status"] = str(kwargs["status"])

        # Validate sort fields
        for sort_field in pagination.sort_spec:
            if sort_field.name not in self.SORTABLE_FIELDS:
                raise ValueError(
                    f"Unknown sort field: {sort_field.name}. "
                    f"Valid fields: {', '.join(sorted(self.SORTABLE_FIELDS))}"
                )

        # Handle cursor if present
        cursor = None
        if pagination.has_cursor():
            cursor = pagination.decode_cursor()
            if cursor is not None:
                cursor.validate_state(pagination.sort_spec, filters_dict)

        # Execute paginated query
        return await self._execute_paginated_query(
            query=query,
            sort_fields=pagination.sort_spec,
            cursor=cursor,
            limit=pagination.limit,
        )
