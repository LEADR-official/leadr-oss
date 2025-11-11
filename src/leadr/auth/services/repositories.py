"""API Key and Device repository services."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from leadr.auth.adapters.orm import (
    APIKeyORM,
    APIKeyStatusEnum,
    DeviceORM,
    DeviceSessionORM,
    DeviceStatusEnum,
)
from leadr.auth.domain.api_key import APIKey, APIKeyStatus
from leadr.auth.domain.device import Device, DeviceSession, DeviceStatus
from leadr.common.repositories import BaseRepository


class APIKeyRepository(BaseRepository[APIKey, APIKeyORM]):
    """API Key repository for managing API key persistence."""

    def _to_domain(self, orm: APIKeyORM) -> APIKey:
        """Convert ORM model to domain entity."""
        return APIKey(
            id=orm.id,
            account_id=orm.account_id,
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
            id=entity.id,
            account_id=entity.account_id,
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
        account_id: UUID,
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
        """
        query = select(APIKeyORM).where(
            APIKeyORM.account_id == account_id,
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

    async def count_active_by_account(self, account_id: UUID) -> int:
        """Count active, non-deleted API keys for a given account.

        Args:
            account_id: The account ID to count keys for.

        Returns:
            Number of active, non-deleted API keys for the account.
        """
        return await self._count_where(
            APIKeyORM.account_id == account_id,
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

    async def get_by_game_and_device_id(self, game_id: UUID, device_id: str) -> Device | None:
        """Get device by game_id and device_id, returns None if not found or soft-deleted.

        Args:
            game_id: The game ID
            device_id: The client-generated device identifier

        Returns:
            Device if found and not deleted, None otherwise
        """
        query = select(DeviceORM).where(
            DeviceORM.game_id == game_id,
            DeviceORM.device_id == device_id,
            DeviceORM.deleted_at.is_(None),
        )
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def filter(
        self,
        account_id: UUID,
        game_id: UUID | None = None,
        status: DeviceStatus | None = None,
        **kwargs,
    ) -> list[Device]:
        """Filter devices by account and optional criteria.

        Args:
            account_id: REQUIRED - Account ID to filter by (multi-tenant safety)
            game_id: Optional game ID to filter by
            status: Optional DeviceStatus to filter by

        Returns:
            List of devices for the account matching the filter criteria
        """
        query = select(DeviceORM).where(
            DeviceORM.account_id == account_id,
            DeviceORM.deleted_at.is_(None),
        )

        if game_id is not None:
            query = query.where(DeviceORM.game_id == game_id)

        if status is not None:
            status_value = status.value if isinstance(status, DeviceStatus) else status
            query = query.where(DeviceORM.status == DeviceStatusEnum(status_value))

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

    async def filter(
        self,
        account_id: UUID,
        device_id: UUID | None = None,
        **kwargs,
    ) -> list[DeviceSession]:
        """Filter sessions by account and optional criteria.

        Note: account_id is used for multi-tenant safety via JOIN with devices table.

        Args:
            account_id: REQUIRED - Account ID to filter by (multi-tenant safety)
            device_id: Optional device ID to filter by

        Returns:
            List of sessions matching the filter criteria
        """
        # Join with devices table to filter by account_id
        query = (
            select(DeviceSessionORM)
            .join(DeviceORM, DeviceSessionORM.device_id == DeviceORM.id)
            .where(
                DeviceORM.account_id == account_id,
                DeviceSessionORM.deleted_at.is_(None),
            )
        )

        if device_id is not None:
            query = query.where(DeviceSessionORM.device_id == device_id)

        result = await self.session.execute(query)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]
