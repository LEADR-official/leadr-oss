"""Account and User repository services."""

from typing import Any, overload

from pydantic import UUID4
from sqlalchemy import select

from leadr.accounts.adapters.orm import AccountORM, AccountStatusEnum, UserORM
from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.domain.user import User
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import AccountID, PrefixedID, UserID
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.common.repositories import BaseRepository


class AccountRepository(BaseRepository[Account, AccountORM]):
    """Account repository for managing account persistence."""

    # Valid sortable fields for accounts
    SORTABLE_FIELDS = {
        "id",
        "name",
        "slug",
        "created_at",
        "updated_at",
    }

    def _to_domain(self, orm: AccountORM) -> Account:
        """Convert ORM model to domain entity."""
        return Account(
            id=AccountID(orm.id),
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
            id=entity.id.uuid,
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

    @overload
    async def filter(
        self,
        account_id: UUID4 | PrefixedID | None = None,
        pagination: None = None,
        **kwargs: Any,
    ) -> list[Account]: ...

    @overload
    async def filter(
        self,
        account_id: UUID4 | PrefixedID | None = None,
        pagination: PaginationParams = ...,
        **kwargs: Any,
    ) -> PaginatedResult[Account]: ...

    async def filter(
        self,
        account_id: UUID4 | PrefixedID | None = None,
        pagination: PaginationParams | None = None,
        **kwargs: Any,
    ) -> list[Account] | PaginatedResult[Account]:
        """Filter accounts by optional criteria with optional pagination.

        Account is the top-level tenant boundary, so no account_id filtering is required.
        The account_id parameter is accepted for interface compatibility but is not used.

        Args:
            account_id: Not used. Account is the top-level tenant.
            pagination: Optional pagination parameters
            status: Optional AccountStatus to filter by
            slug: Optional slug to filter by
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            List of accounts if no pagination, PaginatedResult if pagination provided

        Raises:
            ValueError: If sort field is not in SORTABLE_FIELDS
            CursorValidationError: If cursor is invalid or state doesn't match
        """
        # Note: account_id is intentionally unused - Account is the tenant boundary
        query = select(AccountORM).where(AccountORM.deleted_at.is_(None))

        # Build filters dict for cursor validation
        filters_dict = {}

        # Apply optional filters
        if "status" in kwargs and kwargs["status"] is not None:
            status_value = kwargs["status"]
            if isinstance(status_value, AccountStatus):
                status_value = status_value.value
            query = query.where(AccountORM.status == AccountStatusEnum(status_value))
            filters_dict["status"] = status_value

        if "slug" in kwargs and kwargs["slug"] is not None:
            query = query.where(AccountORM.slug == kwargs["slug"])
            filters_dict["slug"] = kwargs["slug"]

        # If no pagination, return list (backward compatibility)
        if pagination is None:
            result = await self.session.execute(query)
            orms = result.scalars().all()
            return [self._to_domain(orm) for orm in orms]

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


class UserRepository(BaseRepository[User, UserORM]):
    """User repository for managing user persistence."""

    # Valid sortable fields for users
    SORTABLE_FIELDS = {
        "id",
        "email",
        "display_name",
        "created_at",
        "updated_at",
    }

    def _to_domain(self, orm: UserORM) -> User:
        """Convert ORM model to domain entity."""
        return User(
            id=UserID(orm.id),
            account_id=AccountID(orm.account_id),
            email=orm.email,
            display_name=orm.display_name,
            super_admin=orm.super_admin,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            deleted_at=orm.deleted_at,
        )

    def _to_orm(self, entity: User) -> UserORM:
        """Convert domain entity to ORM model."""
        return UserORM(
            id=entity.id.uuid,
            account_id=entity.account_id.uuid,
            email=entity.email,
            display_name=entity.display_name,
            super_admin=entity.super_admin,
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

    @overload
    async def filter(
        self,
        account_id: UUID4 | PrefixedID | None = None,
        pagination: None = None,
        **kwargs: Any,
    ) -> list[User]: ...

    @overload
    async def filter(
        self,
        account_id: UUID4 | PrefixedID | None = None,
        pagination: PaginationParams = ...,
        **kwargs: Any,
    ) -> PaginatedResult[User]: ...

    async def filter(
        self,
        account_id: UUID4 | PrefixedID | None = None,
        pagination: PaginationParams | None = None,
        **kwargs: Any,
    ) -> list[User] | PaginatedResult[User]:
        """Filter users by account and optional criteria with optional pagination.

        Args:
            account_id: Optional account ID to filter by. If None, returns all users
                (superadmin use case). Regular users should always pass account_id.
            pagination: Optional pagination parameters
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            List of users if no pagination, PaginatedResult if pagination provided

        Raises:
            ValueError: If sort field is not in SORTABLE_FIELDS
            CursorValidationError: If cursor is invalid or state doesn't match
        """
        query = select(UserORM).where(UserORM.deleted_at.is_(None))
        if account_id is not None:
            account_uuid = self._extract_uuid(account_id)
            query = query.where(UserORM.account_id == account_uuid)

        # Build filters dict for cursor validation
        filters_dict = {}

        # Future: Add additional filters here as needed
        # if "status" in kwargs:
        #     query = query.where(UserORM.status == kwargs["status"])
        #     filters_dict["status"] = kwargs["status"]

        # If no pagination, return list (backward compatibility)
        if pagination is None:
            result = await self.session.execute(query)
            orms = result.scalars().all()
            return [self._to_domain(orm) for orm in orms]

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

    async def find_superadmins(self) -> list[User]:
        """Find all superadmin users.

        Returns:
            List of all users with super_admin=True (not deleted).
        """
        query = select(UserORM).where(
            UserORM.super_admin.is_(True),
            UserORM.deleted_at.is_(None),
        )

        result = await self.session.execute(query)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]
