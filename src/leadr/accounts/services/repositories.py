"""Account and User repository services."""

from typing import Any

from sqlalchemy import select

from leadr.accounts.adapters.orm import AccountORM, AccountStatusEnum, UserORM
from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.domain.user import User
from leadr.common.domain.models import EntityID
from leadr.common.repositories import BaseRepository


class AccountRepository(BaseRepository[Account, AccountORM]):
    """Account repository for managing account persistence."""

    def _to_domain(self, orm: AccountORM) -> Account:
        """Convert ORM model to domain entity."""
        return Account(
            id=EntityID(value=orm.id),
            name=orm.name,
            slug=orm.slug,
            status=AccountStatus(orm.status.value),
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            deleted_at=orm.deleted_at,
        )

    def _to_orm(self, entity: Account) -> AccountORM:
        """Convert domain entity to ORM model."""
        return AccountORM(
            id=entity.id.value,
            name=entity.name,
            slug=entity.slug,
            status=AccountStatusEnum(entity.status.value),
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )

    def _get_orm_class(self) -> type[AccountORM]:
        """Get the ORM model class."""
        return AccountORM

    async def get_by_slug(self, slug: str) -> Account | None:
        """Get account by slug, returns None if not found or soft-deleted."""
        return await self._get_by_field("slug", slug)

    async def filter(self, **kwargs: Any) -> list[Account]:
        """Filter accounts by optional criteria.

        Account is the top-level tenant boundary, so no account_id filtering is required.

        Args:
            status: Optional AccountStatus to filter by
            slug: Optional slug to filter by
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            List of accounts matching the filter criteria
        """
        query = select(AccountORM).where(AccountORM.deleted_at.is_(None))

        # Apply optional filters
        if "status" in kwargs and kwargs["status"] is not None:
            status_value = kwargs["status"]
            if isinstance(status_value, AccountStatus):
                status_value = status_value.value
            query = query.where(AccountORM.status == AccountStatusEnum(status_value))

        if "slug" in kwargs and kwargs["slug"] is not None:
            query = query.where(AccountORM.slug == kwargs["slug"])

        result = await self.session.execute(query)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]


class UserRepository(BaseRepository[User, UserORM]):
    """User repository for managing user persistence."""

    def _to_domain(self, orm: UserORM) -> User:
        """Convert ORM model to domain entity."""
        return User(
            id=EntityID(value=orm.id),
            account_id=EntityID(value=orm.account_id),
            email=orm.email,
            display_name=orm.display_name,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            deleted_at=orm.deleted_at,
        )

    def _to_orm(self, entity: User) -> UserORM:
        """Convert domain entity to ORM model."""
        return UserORM(
            id=entity.id.value,
            account_id=entity.account_id.value,
            email=entity.email,
            display_name=entity.display_name,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )

    def _get_orm_class(self) -> type[UserORM]:
        """Get the ORM model class."""
        return UserORM

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email, returns None if not found or soft-deleted."""
        return await self._get_by_field("email", email)

    async def filter(self, account_id: EntityID, **kwargs: Any) -> list[User]:
        """Filter users by account and optional criteria.

        Args:
            account_id: REQUIRED - Account ID to filter by (multi-tenant safety)
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            List of users for the account matching the filter criteria
        """
        query = select(UserORM).where(
            UserORM.account_id == account_id.value,
            UserORM.deleted_at.is_(None),
        )

        # Future: Add additional filters here as needed
        # if "status" in kwargs:
        #     query = query.where(UserORM.status == kwargs["status"])

        result = await self.session.execute(query)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]
