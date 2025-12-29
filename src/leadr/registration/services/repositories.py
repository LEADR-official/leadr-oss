"""Registration repository services for verification codes and jam codes."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select

from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import AccountID
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.common.repositories import BaseRepository
from leadr.registration.adapters.orm import (
    JamCodeORM,
    JamCodeRedemptionORM,
    VerificationCodeORM,
    VerificationCodeStatusEnum,
)
from leadr.registration.domain.jam_code import JamCode
from leadr.registration.domain.jam_code_redemption import JamCodeRedemption
from leadr.registration.domain.verification_code import VerificationCode


class VerificationCodeRepository(BaseRepository[VerificationCode, VerificationCodeORM]):
    """Verification code repository for managing email verification codes."""

    SORTABLE_FIELDS = {
        "id",
        "email",
        "status",
        "created_at",
        "updated_at",
        "expires_at",
    }

    def _to_domain(self, orm: VerificationCodeORM) -> VerificationCode:
        """Convert ORM model to domain entity."""
        return orm.to_domain()

    def _to_orm(self, entity: VerificationCode) -> VerificationCodeORM:
        """Convert domain entity to ORM model."""
        return VerificationCodeORM.from_domain(entity)

    def _get_orm_class(self) -> type[VerificationCodeORM]:
        """Get the ORM model class."""
        return VerificationCodeORM

    async def filter(
        self,
        account_id: Any | None = None,
        *,
        pagination: PaginationParams,
        **kwargs: Any,
    ) -> PaginatedResult[VerificationCode]:
        """Filter verification codes by criteria with pagination.

        Args:
            account_id: Not used for verification codes (top-level entity).
            pagination: Pagination parameters (required).
            **kwargs: Filter parameters (email, status, etc.)

        Returns:
            Paginated result of matching VerificationCode entities.

        Raises:
            ValueError: If sort field is not in SORTABLE_FIELDS.
            CursorValidationError: If cursor is invalid or state doesn't match.
        """
        query = select(VerificationCodeORM)

        # Build filters dict for cursor validation
        filters_dict: dict[str, str] = {}

        if "email" in kwargs:
            query = query.where(VerificationCodeORM.email == kwargs["email"])
            filters_dict["email"] = kwargs["email"]
        if "status" in kwargs:
            query = query.where(VerificationCodeORM.status == kwargs["status"])
            filters_dict["status"] = str(kwargs["status"])

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

    async def find_valid_code_by_email(self, email: str, code: str) -> VerificationCode | None:
        """Find a valid (pending) verification code by email and code value.

        Args:
            email: The email address.
            code: The verification code.

        Returns:
            The verification code if found and valid, None otherwise.
        """
        query = select(VerificationCodeORM).where(
            VerificationCodeORM.email == email,
            VerificationCodeORM.code == code.upper(),
            VerificationCodeORM.status == VerificationCodeStatusEnum.PENDING,
        )
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def invalidate_codes_for_email(self, email: str) -> None:
        """Mark all pending verification codes for an email as expired.

        Used when generating a new code to invalidate previous ones.

        Args:
            email: The email address.
        """
        query = (
            select(VerificationCodeORM)
            .where(
                VerificationCodeORM.email == email,
                VerificationCodeORM.status == VerificationCodeStatusEnum.PENDING,
            )
            .with_for_update()
        )
        result = await self.session.execute(query)
        codes = result.scalars().all()

        for code_orm in codes:
            code_orm.status = VerificationCodeStatusEnum.EXPIRED

        await self.session.flush()


class JamCodeRepository(BaseRepository[JamCode, JamCodeORM]):
    """Jam code repository for managing promotional codes."""

    SORTABLE_FIELDS = {
        "id",
        "code",
        "active",
        "current_uses",
        "max_uses",
        "created_at",
        "updated_at",
    }

    def _to_domain(self, orm: JamCodeORM) -> JamCode:
        """Convert ORM model to domain entity."""
        return orm.to_domain()

    def _to_orm(self, entity: JamCode) -> JamCodeORM:
        """Convert domain entity to ORM model."""
        return JamCodeORM.from_domain(entity)

    def _get_orm_class(self) -> type[JamCodeORM]:
        """Get the ORM model class."""
        return JamCodeORM

    async def filter(
        self,
        account_id: Any | None = None,
        *,
        pagination: PaginationParams,
        **kwargs: Any,
    ) -> PaginatedResult[JamCode]:
        """Filter jam codes by criteria with pagination.

        Args:
            account_id: Not used for jam codes (top-level entity).
            pagination: Pagination parameters (required).
            **kwargs: Filter parameters (code, etc.)

        Returns:
            Paginated result of matching JamCode entities.

        Raises:
            ValueError: If sort field is not in SORTABLE_FIELDS.
            CursorValidationError: If cursor is invalid or state doesn't match.
        """
        query = select(JamCodeORM)

        # Build filters dict for cursor validation
        filters_dict: dict[str, str] = {}

        if "code" in kwargs:
            query = query.where(JamCodeORM.code == kwargs["code"].upper())
            filters_dict["code"] = kwargs["code"].upper()

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

    async def find_by_code(self, code: str) -> JamCode | None:
        """Find a jam code by its code value.

        Args:
            code: The jam code to look up (case-insensitive).

        Returns:
            The jam code if found, None otherwise.
        """
        query = select(JamCodeORM).where(JamCodeORM.code == code.upper())
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None


class JamCodeRedemptionRepository(BaseRepository[JamCodeRedemption, JamCodeRedemptionORM]):
    """Jam code redemption repository for tracking code usage."""

    SORTABLE_FIELDS = {
        "id",
        "account_id",
        "jam_code_id",
        "created_at",
    }

    def _to_domain(self, orm: JamCodeRedemptionORM) -> JamCodeRedemption:
        """Convert ORM model to domain entity."""
        return orm.to_domain()

    def _to_orm(self, entity: JamCodeRedemption) -> JamCodeRedemptionORM:
        """Convert domain entity to ORM model."""
        return JamCodeRedemptionORM.from_domain(entity)

    def _get_orm_class(self) -> type[JamCodeRedemptionORM]:
        """Get the ORM model class."""
        return JamCodeRedemptionORM

    async def filter(
        self,
        account_id: Any | None = None,
        *,
        pagination: PaginationParams,
        **kwargs: Any,
    ) -> PaginatedResult[JamCodeRedemption]:
        """Filter jam code redemptions by criteria with pagination.

        Args:
            account_id: Optional account ID to filter by.
            pagination: Pagination parameters (required).
            **kwargs: Additional filter parameters.

        Returns:
            Paginated result of matching JamCodeRedemption entities.

        Raises:
            ValueError: If sort field is not in SORTABLE_FIELDS.
            CursorValidationError: If cursor is invalid or state doesn't match.
        """
        query = select(JamCodeRedemptionORM)

        # Build filters dict for cursor validation
        filters_dict: dict[str, str] = {}

        if account_id:
            query = query.where(JamCodeRedemptionORM.account_id == account_id)
            filters_dict["account_id"] = str(account_id)

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

    async def find_by_account(self, account_id: AccountID) -> list[JamCodeRedemption]:
        """Find all jam code redemptions for an account.

        Args:
            account_id: The account ID.

        Returns:
            List of redemptions for the account.
        """
        query = select(JamCodeRedemptionORM).where(
            JamCodeRedemptionORM.account_id == account_id.uuid
        )
        result = await self.session.execute(query)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]

    async def has_redeemed(self, account_id: AccountID, jam_code_id: UUID) -> bool:
        """Check if an account has already redeemed a specific jam code.

        Args:
            account_id: The account ID.
            jam_code_id: The jam code ID.

        Returns:
            True if the account has redeemed this code, False otherwise.
        """
        query = select(JamCodeRedemptionORM).where(
            JamCodeRedemptionORM.account_id == account_id.uuid,
            JamCodeRedemptionORM.jam_code_id == jam_code_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
