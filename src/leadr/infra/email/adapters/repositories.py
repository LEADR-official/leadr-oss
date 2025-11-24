"""Email repository for database operations."""

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

    def _to_orm(self, domain: Email) -> EmailORM:
        """Convert domain entity to ORM model.

        Args:
            domain: Domain entity.

        Returns:
            ORM model instance.
        """
        return EmailORM.from_domain(domain)

    def _get_orm_class(self) -> type[EmailORM]:
        """Get the ORM class for this repository.

        Returns:
            ORM class.
        """
        return EmailORM
