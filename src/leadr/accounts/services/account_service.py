"""Account service for managing account operations."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import AccountID
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.common.services import BaseService
from leadr.common.utils.slug import generate_unique_slug_with_retry


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
        slug: str | None = None,
        timezone: str | None = None,
        country: str | None = None,
        city: str | None = None,
    ) -> Account:
        """Create a new account with optional slug override and geo data.

        If slug is not provided, it will be auto-generated from the name
        with automatic collision handling to ensure global uniqueness.

        Args:
            name: The account name.
            slug: Optional URL-friendly slug. If not provided, auto-generated from name.
            timezone: Optional timezone from GeoIP lookup (e.g., "America/New_York").
            country: Optional country code from GeoIP lookup (e.g., "US").
            city: Optional city name from GeoIP lookup (e.g., "New York").

        Returns:
            The created Account domain entity.

        Raises:
            ValueError: If provided slug already exists.

        Example:
            >>> # Auto-generate slug from name
            >>> account = await service.create_account(name="Acme Corporation")
            >>> # Override with custom slug and geo data
            >>> account = await service.create_account(
            ...     name="Acme Corporation",
            ...     slug="acme-corp",
            ...     timezone="America/New_York",
            ...     country="US",
            ...     city="New York",
            ... )
        """
        # Generate or validate slug
        if slug is None:
            # Auto-generate unique slug from name with collision handling
            async def check_slug_exists(slug_to_check: str) -> bool:
                """Check if slug exists globally."""
                existing = await self.repository.get_by_slug(slug_to_check)
                return existing is not None

            slug = await generate_unique_slug_with_retry(
                base_text=name,
                check_exists=check_slug_exists,
                max_retries=10,
            )
        else:
            # Use provided slug - validation will happen in Account domain model
            # Check for global uniqueness constraint violation
            existing = await self.repository.get_by_slug(slug)
            if existing is not None:
                raise ValueError(f"An account with slug '{slug}' already exists")

        account = Account(
            name=name,
            slug=slug,
            status=AccountStatus.ACTIVE,
            timezone=timezone,
            country=country,
            city=city,
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

    async def list_accounts(
        self,
        *,
        pagination: PaginationParams,
    ) -> PaginatedResult[Account]:
        """List all accounts with pagination.

        Args:
            pagination: Pagination parameters (required).

        Returns:
            PaginatedResult containing Account entities.
        """
        return await self.repository.filter(pagination=pagination)

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

    async def update_account(self, account_id: AccountID, **updates: Any) -> Account:
        """Update account fields.

        Accepts any fields to update as keyword arguments. Only fields
        explicitly provided will be updated, allowing null values to
        clear optional fields.

        Args:
            account_id: The ID of the account to update
            **updates: Field names and values to update

        Returns:
            The updated Account domain entity

        Raises:
            EntityNotFoundError: If the account doesn't exist
        """
        account = await self.get_by_id_or_raise(account_id)

        # Apply all updates atomically - validation runs once at the end
        account = account.model_copy(update=updates)

        return await self.repository.update(account)

    async def delete_account(self, account_id: AccountID) -> None:
        """Soft-delete an account.

        Args:
            account_id: The ID of the account to delete.

        Raises:
            EntityNotFoundError: If the account doesn't exist.
        """
        await self.delete(account_id)
