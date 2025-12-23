"""Email repository for database operations."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.common.repositories import BaseRepository
from leadr.infra.email.adapters.orm import EmailORM
from leadr.infra.email.domain.models import Email


class EmailRepository(BaseRepository[Email, EmailORM]):
    """Repository for Email entities."""

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

    async def filter(  # type: ignore[override] - intentionally unpaginated (internal email queue)
        self, account_id: Any | None = None, **kwargs: Any
    ) -> list[Email]:
        """Filter emails by criteria.

        Args:
            account_id: Not used for emails (top-level entity).
            **kwargs: Filter parameters (to, status, etc.)

        Returns:
            List of matching Email entities.
        """
        query = select(EmailORM)

        # Apply filters based on kwargs
        if "to" in kwargs:
            query = query.where(EmailORM.to == kwargs["to"])
        if "status" in kwargs:
            query = query.where(EmailORM.status == kwargs["status"])

        result = await self.session.execute(query)
        orm_models = result.scalars().all()
        return [self._to_domain(orm) for orm in orm_models]
