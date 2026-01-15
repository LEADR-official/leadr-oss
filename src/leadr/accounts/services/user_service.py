"""User service for managing user operations."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.user import User
from leadr.accounts.services.repositories import UserRepository
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import AccountID, UserID
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.common.services import BaseService


class UserService(BaseService[User, UserRepository]):
    """Service for managing user lifecycle and operations.

    This service orchestrates user creation, updates, and retrieval
    by coordinating between the domain models and repository layer.
    """

    def _create_repository(self, session: AsyncSession) -> UserRepository:
        """Create UserRepository instance."""
        return UserRepository(session)

    def _get_entity_name(self) -> str:
        """Get entity name for error messages."""
        return "User"

    async def create_user(
        self,
        account_id: AccountID,
        email: str,
        display_name: str,
        super_admin: bool = False,
        is_owner: bool = False,
    ) -> User:
        """Create a new user.

        Args:
            account_id: The account ID the user belongs to.
            email: The user's email address.
            display_name: The user's display name.
            super_admin: Whether this user has superadmin privileges (default: False).
            is_owner: Whether this user is the account owner (default: False).

        Returns:
            The created User domain entity.

        Example:
            >>> user = await service.create_user(
            ...     account_id=account_id,
            ...     email="user@example.com",
            ...     display_name="John Doe",
            ... )
        """
        user = User(
            account_id=account_id,
            email=email,
            display_name=display_name,
            super_admin=super_admin,
            is_owner=is_owner,
        )

        return await self.repository.create(user)

    async def get_user(self, user_id: UserID) -> User | None:
        """Get a user by its ID.

        Args:
            user_id: The ID of the user to retrieve.

        Returns:
            The User domain entity if found, None otherwise.
        """
        return await self.get_by_id(user_id)

    async def get_user_by_email(self, email: str) -> User | None:
        """Get a user by their email address.

        Args:
            email: The email address of the user to retrieve.

        Returns:
            The User domain entity if found, None otherwise.
        """
        return await self.repository.get_by_email(email)

    async def list_users_by_account(
        self,
        account_id: AccountID | None,
        *,
        pagination: PaginationParams,
    ) -> PaginatedResult[User]:
        """List all users for an account with pagination.

        Args:
            account_id: The account ID to list users for. If None, returns all users
                (superadmin use case).
            pagination: Pagination parameters (required).

        Returns:
            PaginatedResult containing User entities.
        """
        return await self.repository.filter(account_id, pagination=pagination)

    async def update_user(self, user_id: UserID, **updates: Any) -> User:
        """Update a user's information.

        Accepts any fields to update as keyword arguments. Only fields
        explicitly provided will be updated, allowing null values to
        clear optional fields.

        Args:
            user_id: The ID of the user to update.
            **updates: Field names and values to update

        Returns:
            The updated User domain entity.

        Raises:
            EntityNotFoundError: If the user doesn't exist.
        """
        user = await self.get_by_id_or_raise(user_id)

        for field, value in updates.items():
            setattr(user, field, value)

        return await self.repository.update(user)

    async def delete_user(self, user_id: UserID) -> None:
        """Soft-delete a user.

        Args:
            user_id: The ID of the user to delete.

        Raises:
            EntityNotFoundError: If the user doesn't exist.
        """
        await self.delete(user_id)

    async def find_superadmins(self) -> list[User]:
        """Find all superadmin users.

        Returns:
            List of all users with super_admin=True.
        """
        return await self.repository.find_superadmins()

    async def superadmin_exists(self) -> bool:
        """Check if any superadmin user exists.

        Returns:
            True if at least one superadmin exists, False otherwise.
        """
        superadmins = await self.find_superadmins()
        return len(superadmins) > 0

    async def suspend_user(self, user_id: UserID) -> User:
        """Suspend a user, preventing access.

        Args:
            user_id: The ID of the user to suspend.

        Returns:
            The updated User domain entity.

        Raises:
            EntityNotFoundError: If the user doesn't exist.
        """
        user = await self.get_by_id_or_raise(user_id)
        user.suspend()
        return await self.repository.update(user)

    async def activate_user(self, user_id: UserID) -> User:
        """Activate a user, allowing access.

        Args:
            user_id: The ID of the user to activate.

        Returns:
            The updated User domain entity.

        Raises:
            EntityNotFoundError: If the user doesn't exist.
        """
        user = await self.get_by_id_or_raise(user_id)
        user.activate()
        return await self.repository.update(user)
