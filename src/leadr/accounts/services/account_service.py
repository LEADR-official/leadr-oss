"""Account service for managing account operations."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.models import EntityID


class AccountService:
    """Service for managing account lifecycle and operations.

    This service orchestrates account creation, status management,
    and retrieval by coordinating between the domain models
    and repository layer.
    """

    def __init__(self, session: AsyncSession):
        """Initialize service with database session.

        Args:
            session: The async database session to use for operations.
        """
        self.session = session
        self.repository = AccountRepository(session)

    async def create_account(
        self,
        account_id: EntityID,
        name: str,
        slug: str,
        created_at: datetime,
        updated_at: datetime,
    ) -> Account:
        """Create a new account.

        Args:
            account_id: The ID for the new account.
            name: The account name.
            slug: The URL-friendly slug for the account.
            created_at: The creation timestamp.
            updated_at: The last update timestamp.

        Returns:
            The created Account domain entity.

        Example:
            >>> account = await service.create_account(
            ...     account_id=EntityID.generate(),
            ...     name="Acme Corporation",
            ...     slug="acme-corp",
            ...     created_at=datetime.now(UTC),
            ...     updated_at=datetime.now(UTC),
            ... )
        """
        account = Account(
            id=account_id,
            name=name,
            slug=slug,
            status=AccountStatus.ACTIVE,
            created_at=created_at,
            updated_at=updated_at,
        )

        return await self.repository.create(account)

    async def get_account(self, account_id: EntityID) -> Account | None:
        """Get an account by its ID.

        Args:
            account_id: The ID of the account to retrieve.

        Returns:
            The Account domain entity if found, None otherwise.
        """
        return await self.repository.get_by_id(account_id)

    async def get_account_by_slug(self, slug: str) -> Account | None:
        """Get an account by its slug.

        Args:
            slug: The slug of the account to retrieve.

        Returns:
            The Account domain entity if found, None otherwise.
        """
        return await self.repository.get_by_slug(slug)

    async def list_accounts(self) -> list[Account]:
        """List all accounts.

        Returns:
            List of Account domain entities.
        """
        return await self.repository.list_all()

    async def suspend_account(self, account_id: EntityID) -> Account:
        """Suspend an account, preventing access.

        Args:
            account_id: The ID of the account to suspend.

        Returns:
            The updated Account domain entity.

        Raises:
            EntityNotFoundError: If the account doesn't exist.
        """
        account = await self.repository.get_by_id(account_id)
        if not account:
            raise EntityNotFoundError("Account", str(account_id))

        account.suspend()
        return await self.repository.update(account)

    async def activate_account(self, account_id: EntityID) -> Account:
        """Activate an account, allowing access.

        Args:
            account_id: The ID of the account to activate.

        Returns:
            The updated Account domain entity.

        Raises:
            EntityNotFoundError: If the account doesn't exist.
        """
        account = await self.repository.get_by_id(account_id)
        if not account:
            raise EntityNotFoundError("Account", str(account_id))

        account.activate()
        return await self.repository.update(account)

    async def delete_account(self, account_id: EntityID) -> None:
        """Soft-delete an account.

        Args:
            account_id: The ID of the account to delete.

        Raises:
            EntityNotFoundError: If the account doesn't exist.
        """
        await self.repository.delete(account_id)
