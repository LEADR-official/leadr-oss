"""API Key, Device, and Nonce repository services."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select

from leadr.auth.adapters.orm import (
    APIKeyORM,
    APIKeyStatusEnum,
    DeviceORM,
    DeviceSessionORM,
    DeviceStatusEnum,
    NonceORM,
)
from leadr.auth.domain.api_key import APIKey, APIKeyStatus
from leadr.auth.domain.device import Device, DeviceSession
from leadr.auth.domain.nonce import Nonce
from leadr.common.domain.ids import (
    AccountID,
    APIKeyID,
    DeviceID,
    GameID,
    UserID,
)
from leadr.common.repositories import BaseRepository


class APIKeyRepository(BaseRepository[APIKey, APIKeyORM]):
    """API Key repository for managing API key persistence."""

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

    async def filter(  # type: ignore[override]
        self,
        account_id: AccountID | None = None,
        status: APIKeyStatus | None = None,
        active_only: bool = False,
        **kwargs,
    ) -> list[APIKey]:
        """Filter API keys by account and optional criteria.

        Args:
            account_id: REQUIRED - Account ID to filter by (multi-tenant safety)
            status: Optional APIKeyStatus to filter by
            active_only: If True, only return ACTIVE keys (bool)

        Returns:
            List of API keys for the account matching the filter criteria

        Raises:
            ValueError: If account_id is None (required for multi-tenant safety)
        """
        if account_id is None:
            raise ValueError("account_id is required for filtering API keys")
        account_uuid = self._extract_uuid(account_id)
        query = select(APIKeyORM).where(
            APIKeyORM.account_id == account_uuid,
            APIKeyORM.deleted_at.is_(None),
        )

        # Apply optional filters
        if status is not None:
            status_value = status.value if isinstance(status, APIKeyStatus) else status
            query = query.where(APIKeyORM.status == APIKeyStatusEnum(status_value))

        if active_only:
            query = query.where(APIKeyORM.status == APIKeyStatusEnum.ACTIVE)

        result = await self.session.execute(query)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]

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

    def _to_domain(self, orm: DeviceORM) -> Device:
        """Convert ORM model to domain entity."""
        return orm.to_domain()

    def _to_orm(self, entity: Device) -> DeviceORM:
        """Convert domain entity to ORM model."""
        return DeviceORM.from_domain(entity)

    def _get_orm_class(self) -> type[DeviceORM]:
        """Get the ORM model class."""
        return DeviceORM

    async def get_by_game_and_device_id(self, game_id: GameID, device_id: str) -> Device | None:
        """Get device by game_id and device_id, returns None if not found or soft-deleted.

        Args:
            game_id: The game ID
            device_id: The client-generated device identifier

        Returns:
            Device if found and not deleted, None otherwise
        """
        game_uuid = self._extract_uuid(game_id)
        query = select(DeviceORM).where(
            DeviceORM.game_id == game_uuid,
            DeviceORM.device_id == device_id,
            DeviceORM.deleted_at.is_(None),
        )
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def filter(  # type: ignore[override]
        self,
        account_id: AccountID | None = None,
        game_id: GameID | None = None,
        status: str | None = None,
        **kwargs,
    ) -> list[Device]:
        """Filter devices by account and optional criteria.

        Args:
            account_id: REQUIRED - Account ID to filter by (multi-tenant safety)
            game_id: Optional game ID to filter by
            status: Optional status string to filter by (active, banned, suspended)

        Returns:
            List of devices for the account matching the filter criteria

        Raises:
            ValueError: If account_id is None (required for multi-tenant safety)
        """
        if account_id is None:
            raise ValueError("account_id is required for filtering devices")
        account_uuid = self._extract_uuid(account_id)
        query = select(DeviceORM).where(
            DeviceORM.account_id == account_uuid,
            DeviceORM.deleted_at.is_(None),
        )

        if game_id is not None:
            game_uuid = self._extract_uuid(game_id)
            query = query.where(DeviceORM.game_id == game_uuid)

        if status is not None:
            query = query.where(DeviceORM.status == DeviceStatusEnum(status))

        result = await self.session.execute(query)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]


class DeviceSessionRepository(BaseRepository[DeviceSession, DeviceSessionORM]):
    """DeviceSession repository for managing device session persistence."""

    def _to_domain(self, orm: DeviceSessionORM) -> DeviceSession:
        """Convert ORM model to domain entity."""
        return orm.to_domain()

    def _to_orm(self, entity: DeviceSession) -> DeviceSessionORM:
        """Convert domain entity to ORM model."""
        return DeviceSessionORM.from_domain(entity)

    def _get_orm_class(self) -> type[DeviceSessionORM]:
        """Get the ORM model class."""
        return DeviceSessionORM

    async def get_by_token_hash(self, token_hash: str) -> DeviceSession | None:
        """Get session by access token hash, returns None if not found or soft-deleted.

        Args:
            token_hash: The hashed access token

        Returns:
            DeviceSession if found and not deleted, None otherwise
        """
        query = select(DeviceSessionORM).where(
            DeviceSessionORM.access_token_hash == token_hash,
            DeviceSessionORM.deleted_at.is_(None),
        )
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_by_refresh_token_hash(self, refresh_token_hash: str) -> DeviceSession | None:
        """Get session by refresh token hash, returns None if not found or soft-deleted.

        Args:
            refresh_token_hash: The hashed refresh token

        Returns:
            DeviceSession if found and not deleted, None otherwise
        """
        query = select(DeviceSessionORM).where(
            DeviceSessionORM.refresh_token_hash == refresh_token_hash,
            DeviceSessionORM.deleted_at.is_(None),
        )
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def filter(  # type: ignore[override]
        self,
        account_id: AccountID | None = None,
        device_id: DeviceID | None = None,
        **kwargs,
    ) -> list[DeviceSession]:
        """Filter sessions by account and optional criteria.

        Note: account_id is used for multi-tenant safety via JOIN with devices table.

        Args:
            account_id: REQUIRED - Account ID to filter by (multi-tenant safety)
            device_id: Optional device ID to filter by

        Returns:
            List of sessions matching the filter criteria

        Raises:
            ValueError: If account_id is None (required for multi-tenant safety)
        """
        if account_id is None:
            raise ValueError("account_id is required for filtering device sessions")
        account_uuid = self._extract_uuid(account_id)
        # Join with devices table to filter by account_id
        query = (
            select(DeviceSessionORM)
            .join(DeviceORM, DeviceSessionORM.device_id == DeviceORM.id)
            .where(
                DeviceORM.account_id == account_uuid,
                DeviceSessionORM.deleted_at.is_(None),
            )
        )

        if device_id is not None:
            device_uuid = self._extract_uuid(device_id)
            query = query.where(DeviceSessionORM.device_id == device_uuid)

        result = await self.session.execute(query)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]


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

    async def filter(  # type: ignore[override]
        self,
        account_id: AccountID | None = None,
        device_id: DeviceID | None = None,
        **kwargs,
    ) -> list[Nonce]:
        """Filter nonces by account and optional criteria.

        Note: account_id is used for multi-tenant safety via JOIN with devices table.

        Args:
            account_id: REQUIRED - Account ID to filter by (multi-tenant safety)
            device_id: Optional device ID to filter by

        Returns:
            List of nonces matching the filter criteria

        Raises:
            ValueError: If account_id is None (required for multi-tenant safety)
        """
        if account_id is None:
            raise ValueError("account_id is required for filtering nonces")
        account_uuid = self._extract_uuid(account_id)
        # Join with devices table to filter by account_id
        query = (
            select(NonceORM)
            .join(DeviceORM, NonceORM.device_id == DeviceORM.id)
            .where(
                DeviceORM.account_id == account_uuid,
                NonceORM.deleted_at.is_(None),
            )
        )

        if device_id is not None:
            device_uuid = self._extract_uuid(device_id)
            query = query.where(NonceORM.device_id == device_uuid)

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
