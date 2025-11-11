"""API Key repository service."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from leadr.auth.adapters.orm import APIKeyORM, APIKeyStatusEnum
from leadr.auth.domain.api_key import APIKey, APIKeyStatus
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
