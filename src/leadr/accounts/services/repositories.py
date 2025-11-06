"""Account and User repository services."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.adapters.orm import AccountORM, AccountStatusEnum, UserORM
from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.domain.user import User
from leadr.common.domain.models import EntityID


class AccountRepository:
    """Account repository for managing account persistence."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    def _to_domain(self, orm: AccountORM) -> Account:
        """Convert ORM model to domain entity."""
        return Account(
            id=EntityID(value=orm.id),
            name=orm.name,  # type: ignore[arg-type]
            slug=orm.slug,  # type: ignore[arg-type]
            status=AccountStatus(orm.status.value),  # type: ignore[attr-defined]
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    def _to_orm(self, domain: Account) -> AccountORM:
        """Convert domain entity to ORM model."""
        return AccountORM(
            id=domain.id.value,
            name=domain.name,
            slug=domain.slug,
            status=AccountStatusEnum(domain.status.value),
            created_at=domain.created_at,
            updated_at=domain.updated_at,
        )

    async def create(self, account: Account) -> Account:
        """Create a new account in the database."""
        orm = self._to_orm(account)
        self.session.add(orm)
        await self.session.commit()
        await self.session.refresh(orm)
        return self._to_domain(orm)

    async def get_by_id(self, account_id: EntityID) -> Account | None:
        """Get account by ID, returns None if not found."""
        result = await self.session.execute(
            select(AccountORM).where(AccountORM.id == account_id.value)  # type: ignore[arg-type]
        )
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_by_slug(self, slug: str) -> Account | None:
        """Get account by slug, returns None if not found."""
        result = await self.session.execute(select(AccountORM).where(AccountORM.slug == slug))  # type: ignore[arg-type]
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def update(self, account: Account) -> Account:
        """Update an existing account in the database."""
        # Fetch the ORM object
        result = await self.session.execute(
            select(AccountORM).where(AccountORM.id == account.id.value)  # type: ignore[arg-type]
        )
        orm = result.scalar_one()

        # Update fields
        orm.name = account.name  # type: ignore[assignment]
        orm.slug = account.slug  # type: ignore[assignment]
        orm.status = AccountStatusEnum(account.status.value)  # type: ignore[assignment]

        await self.session.commit()
        await self.session.refresh(orm)
        return self._to_domain(orm)

    async def delete(self, account_id: EntityID) -> None:
        """Delete an account from the database."""
        await self.session.execute(
            delete(AccountORM).where(AccountORM.id == account_id.value)  # type: ignore[arg-type]
        )
        await self.session.commit()

    async def list_all(self) -> list[Account]:
        """List all accounts in the database."""
        result = await self.session.execute(select(AccountORM))
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]


class UserRepository:
    """User repository for managing user persistence."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    def _to_domain(self, orm: UserORM) -> User:
        """Convert ORM model to domain entity."""
        return User(
            id=EntityID(value=orm.id),
            account_id=EntityID(value=orm.account_id),  # type: ignore[arg-type]
            email=orm.email,  # type: ignore[arg-type]
            display_name=orm.display_name,  # type: ignore[arg-type]
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    def _to_orm(self, domain: User) -> UserORM:
        """Convert domain entity to ORM model."""
        return UserORM(
            id=domain.id.value,
            account_id=domain.account_id.value,
            email=domain.email,
            display_name=domain.display_name,
            created_at=domain.created_at,
            updated_at=domain.updated_at,
        )

    async def create(self, user: User) -> User:
        """Create a new user in the database."""
        orm = self._to_orm(user)
        self.session.add(orm)
        await self.session.commit()
        await self.session.refresh(orm)
        return self._to_domain(orm)

    async def get_by_id(self, user_id: EntityID) -> User | None:
        """Get user by ID, returns None if not found."""
        result = await self.session.execute(
            select(UserORM).where(UserORM.id == user_id.value)  # type: ignore[arg-type]
        )
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email, returns None if not found."""
        result = await self.session.execute(select(UserORM).where(UserORM.email == email))  # type: ignore[arg-type]
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_by_account(self, account_id: EntityID) -> list[User]:
        """List all users for a given account."""
        result = await self.session.execute(
            select(UserORM).where(UserORM.account_id == account_id.value)  # type: ignore[arg-type]
        )
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]

    async def update(self, user: User) -> User:
        """Update an existing user in the database."""
        # Fetch the ORM object
        result = await self.session.execute(
            select(UserORM).where(UserORM.id == user.id.value)  # type: ignore[arg-type]
        )
        orm = result.scalar_one()

        # Update fields (note: account_id is immutable so we don't update it)
        orm.email = user.email  # type: ignore[assignment]
        orm.display_name = user.display_name  # type: ignore[assignment]

        await self.session.commit()
        await self.session.refresh(orm)
        return self._to_domain(orm)

    async def delete(self, user_id: EntityID) -> None:
        """Delete a user from the database."""
        await self.session.execute(
            delete(UserORM).where(UserORM.id == user_id.value)  # type: ignore[arg-type]
        )
        await self.session.commit()
