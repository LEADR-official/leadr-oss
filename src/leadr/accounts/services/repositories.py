"""Account and User repository services."""

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
        result = await self.session.execute(
            select(AccountORM).where(AccountORM.slug == slug, AccountORM.deleted_at.is_(None))
        )
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None


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
        result = await self.session.execute(
            select(UserORM).where(UserORM.email == email, UserORM.deleted_at.is_(None))
        )
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_by_account(self, account_id: EntityID) -> list[User]:
        """List all non-deleted users for a given account."""
        result = await self.session.execute(
            select(UserORM).where(
                UserORM.account_id == account_id.value, UserORM.deleted_at.is_(None)
            )
        )
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]
