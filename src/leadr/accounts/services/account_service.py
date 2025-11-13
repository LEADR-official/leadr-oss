"""Account service for managing account operations."""

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository
from leadr.common.domain.ids import AccountID
from leadr.common.services import BaseService


class AccountService(BaseService[Account, AccountRepository]):
    """Service for managing account lifecycle and operations.

    This service orchestrates account creation, status management,
    and retrieval by coordinating between the domain models
    and repository layer.
    """

    def _create_repository(self, session: AsyncSession) -> AccountRepository:
        """Create AccountRepository instance."""
        return AccountRepository(session)

    def _get_entity_name(self) -> str:
        """Get entity name for error messages."""
        return "Account"

    async def create_account(
        self,
        name: str,
        slug: str,
    ) -> Account:
        """Create a new account.

        Args:
            name: The account name.
            slug: The URL-friendly slug for the account.

        Returns:
            The created Account domain entity.

        Example:
            >>> account = await service.create_account(
            ...     name="Acme Corporation",
            ...     slug="acme-corp",
            ... )
        """
        account = Account(
            name=name,
            slug=slug,
            status=AccountStatus.ACTIVE,
        )

        return await self.repository.create(account)

    async def get_account(self, account_id: AccountID) -> Account | None:
        """Get an account by its ID.

        Args:
            account_id: The ID of the account to retrieve.

        Returns:
            The Account domain entity if found, None otherwise.
        """
        return await self.get_by_id(account_id)

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
        return await self.repository.filter()

    async def suspend_account(self, account_id: AccountID) -> Account:
        """Suspend an account, preventing access.

        Args:
            account_id: The ID of the account to suspend.

        Returns:
            The updated Account domain entity.

        Raises:
            EntityNotFoundError: If the account doesn't exist.
        """
        account = await self.get_by_id_or_raise(account_id)
        account.suspend()
        return await self.repository.update(account)

    async def activate_account(self, account_id: AccountID) -> Account:
        """Activate an account, allowing access.

        Args:
            account_id: The ID of the account to activate.

        Returns:
            The updated Account domain entity.

        Raises:
            EntityNotFoundError: If the account doesn't exist.
        """
        account = await self.get_by_id_or_raise(account_id)
        account.activate()
        return await self.repository.update(account)

    async def update_account(
        self,
        account_id: AccountID,
        name: str | None = None,
        slug: str | None = None,
    ) -> Account:
        """Update account fields.

        Args:
            account_id: The ID of the account to update
            name: New account name, if provided
            slug: New account slug, if provided

        Returns:
            The updated Account domain entity

        Raises:
            EntityNotFoundError: If the account doesn't exist
        """
        account = await self.get_by_id_or_raise(account_id)

        if name is not None:
            account.name = name
        if slug is not None:
            account.slug = slug

        return await self.repository.update(account)

    async def delete_account(self, account_id: AccountID) -> None:
        """Soft-delete an account.

        Args:
            account_id: The ID of the account to delete.

        Raises:
            EntityNotFoundError: If the account doesn't exist.
        """
        await self.delete(account_id)
