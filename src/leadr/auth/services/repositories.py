"""API Key repository service."""

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.auth.adapters.orm import APIKeyORM, APIKeyStatusEnum
from leadr.auth.domain.api_key import APIKey, APIKeyStatus
from leadr.common.domain.models import EntityID


class APIKeyRepository:
    """API Key repository for managing API key persistence."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

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
        )

    def _to_orm(self, domain: APIKey) -> APIKeyORM:
        """Convert domain entity to ORM model."""
        return APIKeyORM(
            id=domain.id.value,
            account_id=domain.account_id.value,
            name=domain.name,
            key_hash=domain.key_hash,
            key_prefix=domain.key_prefix,
            status=APIKeyStatusEnum(domain.status.value),
            last_used_at=domain.last_used_at,
            expires_at=domain.expires_at,
            created_at=domain.created_at,
            updated_at=domain.updated_at,
        )

    async def create(self, api_key: APIKey) -> APIKey:
        """Create a new API key in the database."""
        orm = self._to_orm(api_key)
        self.session.add(orm)
        await self.session.commit()
        await self.session.refresh(orm)
        return self._to_domain(orm)

    async def get_by_id(self, key_id: EntityID) -> APIKey | None:
        """Get API key by ID, returns None if not found."""
        result = await self.session.execute(select(APIKeyORM).where(APIKeyORM.id == key_id.value))
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_by_prefix(self, key_prefix: str) -> APIKey | None:
        """Get API key by prefix, returns None if not found."""
        result = await self.session.execute(
            select(APIKeyORM).where(APIKeyORM.key_prefix == key_prefix)
        )
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_by_account(
        self, account_id: EntityID, active_only: bool = False
    ) -> list[APIKey]:
        """List API keys for a given account.

        Args:
            account_id: The account ID to filter by.
            active_only: If True, only return keys with ACTIVE status.

        Returns:
            List of API keys belonging to the account.
        """
        query = select(APIKeyORM).where(APIKeyORM.account_id == account_id.value)

        if active_only:
            query = query.where(APIKeyORM.status == APIKeyStatusEnum.ACTIVE)

        result = await self.session.execute(query)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]

    async def count_active_by_account(self, account_id: EntityID) -> int:
        """Count active API keys for a given account.

        Args:
            account_id: The account ID to count keys for.

        Returns:
            Number of active API keys for the account.
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(APIKeyORM)
            .where(
                APIKeyORM.account_id == account_id.value,
                APIKeyORM.status == APIKeyStatusEnum.ACTIVE,
            )
        )
        return result.scalar_one()

    async def update(self, api_key: APIKey) -> APIKey:
        """Update an existing API key in the database."""
        # Fetch the ORM object
        result = await self.session.execute(
            select(APIKeyORM).where(APIKeyORM.id == api_key.id.value)
        )
        orm = result.scalar_one()

        # Update fields
        orm.name = api_key.name
        orm.key_hash = api_key.key_hash
        orm.key_prefix = api_key.key_prefix
        orm.status = APIKeyStatusEnum(api_key.status.value)
        orm.last_used_at = api_key.last_used_at
        orm.expires_at = api_key.expires_at

        await self.session.commit()
        await self.session.refresh(orm)
        return self._to_domain(orm)

    async def delete(self, key_id: EntityID) -> None:
        """Delete an API key from the database."""
        await self.session.execute(delete(APIKeyORM).where(APIKeyORM.id == key_id.value))
        await self.session.commit()
