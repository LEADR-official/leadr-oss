"""API Key, Device, Identity, and Nonce repository services."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import delete, select

from leadr.auth.adapters.orm import (
    APIKeyORM,
    APIKeyStatusEnum,
    DeviceORM,
    DeviceStatusEnum,
    IdentityKindEnum,
    IdentityORM,
    IdentitySessionORM,
    NonceORM,
)
from leadr.auth.domain.api_key import APIKey, APIKeyStatus
from leadr.auth.domain.device import Device
from leadr.auth.domain.identity import Identity, IdentityKind, IdentitySession
from leadr.auth.domain.nonce import Nonce
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import (
    AccountID,
    APIKeyID,
    GameID,
    IdentityID,
    UserID,
)
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.common.repositories import BaseRepository


class APIKeyRepository(BaseRepository[APIKey, APIKeyORM]):
    """API Key repository for managing API key persistence."""

    # Valid sortable fields for API keys
    SORTABLE_FIELDS = {
        "id",
        "name",
        "created_at",
        "updated_at",
    }

    def _to_domain(self, orm: APIKeyORM) -> APIKey:
        """Convert ORM model to domain entity."""
        return APIKey(
            id=APIKeyID(orm.id),
            account_id=AccountID(orm.account_id),
            user_id=UserID(orm.user_id),
            name=orm.name,
            key_hash=orm.key_hash,
            key_prefix=orm.key_prefix,
            status=APIKeyStatus(orm.status.value),
            last_used_at=orm.last_used_at,
            expires_at=orm.expires_at,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            deleted_at=orm.deleted_at,
        )

    def _to_orm(self, entity: APIKey) -> APIKeyORM:
        """Convert domain entity to ORM model."""
        return APIKeyORM(
            id=entity.id.uuid,
            account_id=entity.account_id.uuid,
            user_id=entity.user_id.uuid,
            name=entity.name,
            key_hash=entity.key_hash,
            key_prefix=entity.key_prefix,
            status=APIKeyStatusEnum(entity.status.value),
            last_used_at=entity.last_used_at,
            expires_at=entity.expires_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )

    def _get_orm_class(self) -> type[APIKeyORM]:
        """Get the ORM model class."""
        return APIKeyORM

    async def get_by_prefix(self, key_prefix: str) -> APIKey | None:
        """Get API key by prefix, returns None if not found or soft-deleted."""
        return await self._get_by_field("key_prefix", key_prefix)

    async def filter(
        self,
        account_id: AccountID | None = None,
        *,
        status: APIKeyStatus | None = None,
        active_only: bool = False,
        pagination: PaginationParams,
        **kwargs: Any,
    ) -> PaginatedResult[APIKey]:
        """Filter API keys by account and optional criteria with pagination.

        Args:
            account_id: Optional account ID to filter by. If None, returns all API keys
                (superadmin use case). Regular users should always pass account_id.
            status: Optional APIKeyStatus to filter by
            active_only: If True, only return ACTIVE keys (bool)
            pagination: Pagination parameters (required).
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            PaginatedResult containing API keys.

        Raises:
            ValueError: If sort field is not in SORTABLE_FIELDS
            CursorValidationError: If cursor is invalid or state doesn't match
        """
        query = select(APIKeyORM).where(APIKeyORM.deleted_at.is_(None))
        if account_id is not None:
            account_uuid = self._extract_uuid(account_id)
            query = query.where(APIKeyORM.account_id == account_uuid)

        # Build filters dict for cursor validation
        filters_dict: dict[str, str] = {}

        # Apply optional filters
        if status is not None:
            status_value = status.value if isinstance(status, APIKeyStatus) else status
            query = query.where(APIKeyORM.status == APIKeyStatusEnum(status_value))
            filters_dict["status"] = status_value

        if active_only:
            query = query.where(APIKeyORM.status == APIKeyStatusEnum.ACTIVE)
            filters_dict["active_only"] = "true"

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

    async def count_active_by_account(self, account_id: AccountID) -> int:
        """Count active, non-deleted API keys for a given account.

        Args:
            account_id: The account ID to count keys for.

        Returns:
            Number of active, non-deleted API keys for the account.
        """
        account_uuid = self._extract_uuid(account_id)
        return await self._count_where(
            APIKeyORM.account_id == account_uuid,
            APIKeyORM.status == APIKeyStatusEnum.ACTIVE,
            APIKeyORM.deleted_at.is_(None),
        )


class DeviceRepository(BaseRepository[Device, DeviceORM]):
    """Device repository for managing device persistence."""

    # Valid sortable fields for devices
    SORTABLE_FIELDS = {
        "id",
        "platform",
        "created_at",
        "updated_at",
    }

    def _to_domain(self, orm: DeviceORM) -> Device:
        """Convert ORM model to domain entity."""
        return orm.to_domain()

    def _to_orm(self, entity: Device) -> DeviceORM:
        """Convert domain entity to ORM model."""
        return DeviceORM.from_domain(entity)

    def _get_orm_class(self) -> type[DeviceORM]:
        """Get the ORM model class."""
        return DeviceORM

    async def get_by_game_and_fingerprint(
        self, game_id: GameID, client_fingerprint: str
    ) -> Device | None:
        """Get device by game_id and client_fingerprint, returns None if not found or soft-deleted.

        Args:
            game_id: The game ID
            client_fingerprint: The client-generated SHA256 device fingerprint

        Returns:
            Device if found and not deleted, None otherwise
        """
        game_uuid = self._extract_uuid(game_id)
        query = select(DeviceORM).where(
            DeviceORM.game_id == game_uuid,
            DeviceORM.client_fingerprint == client_fingerprint,
            DeviceORM.deleted_at.is_(None),
        )
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def filter(
        self,
        account_id: AccountID | None = None,
        *,
        game_id: GameID | None = None,
        status: str | None = None,
        pagination: PaginationParams,
        **kwargs: Any,
    ) -> PaginatedResult[Device]:
        """Filter devices by account and optional criteria with pagination.

        Args:
            account_id: Optional account ID to filter by. If None, returns all devices
                (superadmin use case). Regular users should always pass account_id.
            game_id: Optional game ID to filter by
            status: Optional status string to filter by (active, banned, suspended)
            pagination: Pagination parameters (required).
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            PaginatedResult containing devices.

        Raises:
            ValueError: If sort field is not in SORTABLE_FIELDS
            CursorValidationError: If cursor is invalid or state doesn't match
        """
        query = select(DeviceORM).where(DeviceORM.deleted_at.is_(None))
        if account_id is not None:
            account_uuid = self._extract_uuid(account_id)
            query = query.where(DeviceORM.account_id == account_uuid)

        # Build filters dict for cursor validation
        filters_dict: dict[str, str] = {}

        if game_id is not None:
            game_uuid = self._extract_uuid(game_id)
            query = query.where(DeviceORM.game_id == game_uuid)
            filters_dict["game_id"] = str(game_id)

        if status is not None:
            query = query.where(DeviceORM.status == DeviceStatusEnum(status))
            filters_dict["status"] = status

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


class NonceRepository(BaseRepository[Nonce, NonceORM]):
    """Nonce repository for managing nonce persistence."""

    def _to_domain(self, orm: NonceORM) -> Nonce:
        """Convert ORM model to domain entity."""
        return orm.to_domain()

    def _to_orm(self, entity: Nonce) -> NonceORM:
        """Convert domain entity to ORM model."""
        return NonceORM.from_domain(entity)

    def _get_orm_class(self) -> type[NonceORM]:
        """Get the ORM model class."""
        return NonceORM

    async def get_by_nonce_value(self, nonce_value: str) -> Nonce | None:
        """Get nonce by nonce_value, returns None if not found or soft-deleted.

        Args:
            nonce_value: The unique nonce value to search for

        Returns:
            Nonce if found and not deleted, None otherwise
        """
        query = select(NonceORM).where(
            NonceORM.nonce_value == nonce_value,
            NonceORM.deleted_at.is_(None),
        )
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def filter(  # type: ignore[override] - intentionally unpaginated (nonces are short-lived)
        self,
        account_id: AccountID | None = None,
        identity_id: IdentityID | None = None,
        **kwargs: Any,
    ) -> list[Nonce]:
        """Filter nonces by account and optional criteria.

        Note: account_id is used for multi-tenant safety via JOIN with identities table.

        Args:
            account_id: REQUIRED - Account ID to filter by (multi-tenant safety)
            identity_id: Optional identity ID to filter by

        Returns:
            List of nonces matching the filter criteria

        Raises:
            ValueError: If account_id is None (required for multi-tenant safety)
        """
        if account_id is None:
            raise ValueError("account_id is required for filtering nonces")
        account_uuid = self._extract_uuid(account_id)
        # Join with identities table to filter by account_id
        query = (
            select(NonceORM)
            .join(IdentityORM, NonceORM.identity_id == IdentityORM.id)
            .where(
                IdentityORM.account_id == account_uuid,
                NonceORM.deleted_at.is_(None),
            )
        )

        if identity_id is not None:
            identity_uuid = self._extract_uuid(identity_id)
            query = query.where(NonceORM.identity_id == identity_uuid)

        result = await self.session.execute(query)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]

    async def cleanup_expired_nonces(self, before: datetime) -> int:
        """Delete expired nonces older than specified time.

        Only deletes nonces with PENDING status. Used and expired nonces
        are kept for audit/debugging purposes.

        Args:
            before: Delete nonces that expired before this datetime

        Returns:
            Number of nonces deleted
        """
        stmt = delete(NonceORM).where(
            NonceORM.expires_at < before,
            NonceORM.status == "pending",
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        # rowcount is available on CursorResult from DELETE statements
        return int(result.rowcount) if result.rowcount else 0  # type: ignore[attr-defined]


class IdentityRepository(BaseRepository[Identity, IdentityORM]):
    """Identity repository for managing identity persistence."""

    # Valid sortable fields for identities
    SORTABLE_FIELDS = {
        "id",
        "display_name",
        "kind",
        "created_at",
        "updated_at",
    }

    def _to_domain(self, orm: IdentityORM) -> Identity:
        """Convert ORM model to domain entity."""
        return orm.to_domain()

    def _to_orm(self, entity: Identity) -> IdentityORM:
        """Convert domain entity to ORM model."""
        return IdentityORM.from_domain(entity)

    def _get_orm_class(self) -> type[IdentityORM]:
        """Get the ORM model class."""
        return IdentityORM

    async def get_by_external_key(
        self,
        account_id: AccountID,
        game_id: GameID,
        kind: IdentityKind,
        external_key: str,
    ) -> Identity | None:
        """Get identity by unique key combination.

        Args:
            account_id: The account ID
            game_id: The game ID
            kind: The identity kind (DEVICE, STEAM, CUSTOM)
            external_key: The external identifier

        Returns:
            Identity if found and not deleted, None otherwise
        """
        account_uuid = self._extract_uuid(account_id)
        game_uuid = self._extract_uuid(game_id)
        query = select(IdentityORM).where(
            IdentityORM.account_id == account_uuid,
            IdentityORM.game_id == game_uuid,
            IdentityORM.kind == IdentityKindEnum(kind.value),
            IdentityORM.external_key == external_key,
            IdentityORM.deleted_at.is_(None),
        )
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def filter(
        self,
        account_id: AccountID | None = None,
        *,
        game_id: GameID | None = None,
        kind: IdentityKind | None = None,
        pagination: PaginationParams,
        **kwargs: Any,
    ) -> PaginatedResult[Identity]:
        """Filter identities by account and optional criteria with pagination.

        Args:
            account_id: Optional account ID to filter by. If None, returns all identities
                (superadmin use case). Regular users should always pass account_id.
            game_id: Optional game ID to filter by
            kind: Optional identity kind to filter by
            pagination: Pagination parameters (required).
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            PaginatedResult containing identities.

        Raises:
            ValueError: If sort field is not in SORTABLE_FIELDS
            CursorValidationError: If cursor is invalid or state doesn't match
        """
        query = select(IdentityORM).where(IdentityORM.deleted_at.is_(None))
        if account_id is not None:
            account_uuid = self._extract_uuid(account_id)
            query = query.where(IdentityORM.account_id == account_uuid)

        # Build filters dict for cursor validation
        filters_dict: dict[str, str] = {}

        if game_id is not None:
            game_uuid = self._extract_uuid(game_id)
            query = query.where(IdentityORM.game_id == game_uuid)
            filters_dict["game_id"] = str(game_id)

        if kind is not None:
            query = query.where(IdentityORM.kind == IdentityKindEnum(kind.value))
            filters_dict["kind"] = kind.value

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


class IdentitySessionRepository(BaseRepository[IdentitySession, IdentitySessionORM]):
    """IdentitySession repository for managing identity session persistence."""

    # Valid sortable fields for identity sessions
    SORTABLE_FIELDS = {
        "id",
        "created_at",
        "updated_at",
    }

    def _to_domain(self, orm: IdentitySessionORM) -> IdentitySession:
        """Convert ORM model to domain entity."""
        return orm.to_domain()

    def _to_orm(self, entity: IdentitySession) -> IdentitySessionORM:
        """Convert domain entity to ORM model."""
        return IdentitySessionORM.from_domain(entity)

    def _get_orm_class(self) -> type[IdentitySessionORM]:
        """Get the ORM model class."""
        return IdentitySessionORM

    async def get_by_token_hash(self, token_hash: str) -> IdentitySession | None:
        """Get session by access token hash, returns None if not found or soft-deleted.

        Args:
            token_hash: The hashed access token

        Returns:
            IdentitySession if found and not deleted, None otherwise
        """
        query = select(IdentitySessionORM).where(
            IdentitySessionORM.access_token_hash == token_hash,
            IdentitySessionORM.deleted_at.is_(None),
        )
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_by_refresh_token_hash(self, refresh_token_hash: str) -> IdentitySession | None:
        """Get session by refresh token hash, returns None if not found or soft-deleted.

        Args:
            refresh_token_hash: The hashed refresh token

        Returns:
            IdentitySession if found and not deleted, None otherwise
        """
        query = select(IdentitySessionORM).where(
            IdentitySessionORM.refresh_token_hash == refresh_token_hash,
            IdentitySessionORM.deleted_at.is_(None),
        )
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def filter(
        self,
        account_id: AccountID | None = None,
        *,
        identity_id: IdentityID | None = None,
        pagination: PaginationParams,
        **kwargs: Any,
    ) -> PaginatedResult[IdentitySession]:
        """Filter sessions by account and optional criteria with pagination.

        Note: account_id is used for multi-tenant safety via JOIN with identities table.

        Args:
            account_id: Optional account ID to filter by. If None, returns all sessions
                (superadmin use case). Regular users should always pass account_id.
            identity_id: Optional identity ID to filter by
            pagination: Pagination parameters (required).
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            PaginatedResult containing identity sessions.

        Raises:
            ValueError: If sort field is not in SORTABLE_FIELDS
            CursorValidationError: If cursor is invalid or state doesn't match
        """
        # Base query without account filter
        query = select(IdentitySessionORM).where(IdentitySessionORM.deleted_at.is_(None))

        # Join with identities table to filter by account_id if provided
        if account_id is not None:
            account_uuid = self._extract_uuid(account_id)
            query = query.join(IdentityORM, IdentitySessionORM.identity_id == IdentityORM.id).where(
                IdentityORM.account_id == account_uuid
            )

        # Build filters dict for cursor validation
        filters_dict: dict[str, str] = {}

        if identity_id is not None:
            identity_uuid = self._extract_uuid(identity_id)
            query = query.where(IdentitySessionORM.identity_id == identity_uuid)
            filters_dict["identity_id"] = str(identity_id)

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
