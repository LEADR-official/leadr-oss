"""API Key repository service."""

from __future__ import annotations

from sqlalchemy import select

from leadr.auth.adapters.orm import APIKeyORM, APIKeyStatusEnum
from leadr.auth.domain.api_key import APIKey, APIKeyStatus
from leadr.common.domain.models import EntityID
from leadr.common.repositories import BaseRepository


class APIKeyRepository(BaseRepository[APIKey, APIKeyORM]):
    """API Key repository for managing API key persistence."""

    def _to_domain(self, orm: APIKeyORM) -> APIKey:
        """Convert ORM model to domain entity."""
        return APIKey(
            id=EntityID(value=orm.id),
            account_id=EntityID(value=orm.account_id),
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
            id=entity.id.value,
            account_id=entity.account_id.value,
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

    async def list(
        self,
        account_id: EntityID | None = None,
        status: APIKeyStatus | None = None,
        include_deleted: bool = False,
    ) -> list[APIKey]:
        """List API keys with optional filters.

        Args:
            account_id: Optional account ID to filter by.
            status: Optional status to filter by.
            include_deleted: If True, include soft-deleted keys. Defaults to False.

        Returns:
            List of API keys matching the filters.
        """
        query = select(APIKeyORM)

        if not include_deleted:
            query = query.where(APIKeyORM.deleted_at.is_(None))

        if account_id is not None:
            query = query.where(APIKeyORM.account_id == account_id.value)

        if status is not None:
            query = query.where(APIKeyORM.status == APIKeyStatusEnum(status.value))

        result = await self.session.execute(query)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]

    async def list_by_account(
        self, account_id: EntityID, active_only: bool = False
    ) -> list[APIKey]:
        """List API keys for a given account, excluding soft-deleted keys.

        Args:
            account_id: The account ID to filter by.
            active_only: If True, only return keys with ACTIVE status.

        Returns:
            List of non-deleted API keys belonging to the account.
        """
        filters = []
        if active_only:
            filters.append(APIKeyORM.status == APIKeyStatusEnum.ACTIVE)
        return await self._list_by_account(account_id, filters if filters else None)

    async def count_active_by_account(self, account_id: EntityID) -> int:
        """Count active, non-deleted API keys for a given account.

        Args:
            account_id: The account ID to count keys for.

        Returns:
            Number of active, non-deleted API keys for the account.
        """
        return await self._count_where(
            APIKeyORM.account_id == account_id.value,
            APIKeyORM.status == APIKeyStatusEnum.ACTIVE,
            APIKeyORM.deleted_at.is_(None),
        )
