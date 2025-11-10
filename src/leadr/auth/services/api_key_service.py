"""API Key service for managing API key operations."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.auth.domain.api_key import APIKey
from leadr.auth.services.api_key_crypto import generate_api_key, hash_api_key, verify_api_key
from leadr.auth.services.repositories import APIKeyRepository
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.services import BaseService
from leadr.config import settings


class APIKeyService(BaseService[APIKey, APIKeyRepository]):
    """Service for managing API key lifecycle and operations.

    This service orchestrates API key creation, validation, and management
    by coordinating between the domain models, cryptographic functions,
    and repository layer.
    """

    def _create_repository(self, session: AsyncSession) -> APIKeyRepository:
        """Create APIKeyRepository instance."""
        return APIKeyRepository(session)

    def _get_entity_name(self) -> str:
        """Get entity name for error messages."""
        return "APIKey"

    async def create_api_key(
        self,
        account_id: UUID,
        name: str,
        expires_at: datetime | None = None,
    ) -> tuple[APIKey, str]:
        """Create a new API key for an account.

        Generates a secure random key, hashes it for storage, and persists
        it to the database. The plain key is returned only once for the
        caller to provide to the user.

        Args:
            account_id: The account ID to create the key for.
            name: A descriptive name for the key.
            expires_at: Optional expiration timestamp for the key.

        Returns:
            A tuple of (APIKey domain entity, plain key string).
            The plain key should be shown to the user once and not stored.

        Example:
            >>> api_key, plain_key = await service.create_api_key(
            ...     account_id=account_id,
            ...     name="Production API Key",
            ...     expires_at=datetime.now(UTC) + timedelta(days=90)
            ... )
            >>> print(f"Your API key: {plain_key}")
            Your API key: ldr_abc123...
        """
        # Generate secure random key
        plain_key = generate_api_key()

        # Hash the key for storage
        key_hash = hash_api_key(plain_key, settings.API_KEY_SECRET)

        # Extract prefix for lookup (first 10 characters including ldr_)
        # Use more characters to ensure uniqueness while keeping searchable
        key_prefix = plain_key[:14]  # ldr_ + 10 chars

        # Create domain entity
        api_key = APIKey(
            account_id=account_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            expires_at=expires_at,
        )

        # Persist to database
        created_key = await self.repository.create(api_key)

        return created_key, plain_key

    async def validate_api_key(self, plain_key: str) -> APIKey | None:
        """Validate an API key and return the domain entity if valid.

        Performs the following checks:
        1. Extracts prefix and looks up key in database
        2. Verifies the hash matches
        3. Checks if key is active (not revoked)
        4. Checks if key is not expired
        5. Records usage timestamp if valid

        Args:
            plain_key: The plain API key string to validate.

        Returns:
            The APIKey domain entity if valid, None otherwise.

        Example:
            >>> api_key = await service.validate_api_key("ldr_abc123...")
            >>> if api_key:
            ...     print(f"Valid key for account {api_key.account_id}")
            ... else:
            ...     print("Invalid or expired key")
        """
        # Extract prefix for lookup
        if len(plain_key) < 14:
            return None

        key_prefix = plain_key[:14]

        # Look up key by prefix
        api_key = await self.repository.get_by_prefix(key_prefix)
        if not api_key:
            return None

        # Verify hash matches
        if not verify_api_key(plain_key, api_key.key_hash, settings.API_KEY_SECRET):
            return None

        # Check if key is valid (active and not expired)
        if not api_key.is_valid():
            return None

        # Record usage
        now = datetime.now(UTC)
        api_key.record_usage(now)
        await self.repository.update(api_key)

        return api_key

    async def get_api_key(self, key_id: UUID) -> APIKey | None:
        """Get an API key by its ID.

        Args:
            key_id: The ID of the API key to retrieve.

        Returns:
            The APIKey domain entity if found, None otherwise.
        """
        return await self.get_by_id(key_id)

    async def list_api_keys(
        self,
        account_id: UUID,
        status: str | None = None,
    ) -> list[APIKey]:
        """List API keys for an account with optional filters.

        Args:
            account_id: REQUIRED - Account ID to filter by (multi-tenant safety).
            status: Optional status string to filter by.

        Returns:
            List of APIKey domain entities matching the filters.
        """
        from leadr.auth.domain.api_key import APIKeyStatus

        # Build filter kwargs
        kwargs = {}
        if status is not None:
            kwargs["status"] = APIKeyStatus(status)

        return await self.repository.filter(account_id, **kwargs)

    async def list_account_api_keys(
        self,
        account_id: UUID,
        active_only: bool = False,
    ) -> list[APIKey]:
        """List all API keys for an account.

        Args:
            account_id: The account ID to list keys for.
            active_only: If True, only return active (non-revoked) keys.

        Returns:
            List of APIKey domain entities.
        """
        kwargs = {}
        if active_only:
            kwargs["active_only"] = True

        return await self.repository.filter(account_id, **kwargs)

    async def count_active_api_keys(self, account_id: UUID) -> int:
        """Count active API keys for an account.

        This is useful for enforcing limits on the number of active keys
        per account based on their plan or tier.

        Args:
            account_id: The account ID to count keys for.

        Returns:
            Number of active (non-revoked) API keys.
        """
        return await self.repository.count_active_by_account(account_id)

    async def update_api_key_status(self, key_id: UUID, status: str) -> APIKey:
        """Update the status of an API key.

        Args:
            key_id: The ID of the API key to update.
            status: The new status value (active or revoked).

        Returns:
            The updated APIKey domain entity.

        Raises:
            EntityNotFoundError: If the key doesn't exist.
            ValueError: If the status is invalid.
        """
        from leadr.auth.domain.api_key import APIKeyStatus

        api_key = await self.repository.get_by_id(key_id)
        if not api_key:
            raise EntityNotFoundError("APIKey", str(key_id))

        # Convert string to enum and update
        status_enum = APIKeyStatus(status)
        if status_enum == APIKeyStatus.REVOKED:
            api_key.revoke()
        else:
            # For other status changes, update directly
            api_key.status = status_enum

        return await self.repository.update(api_key)

    async def revoke_api_key(self, key_id: UUID) -> APIKey:
        """Revoke an API key, preventing further use.

        Args:
            key_id: The ID of the API key to revoke.

        Returns:
            The updated APIKey domain entity with REVOKED status.

        Raises:
            EntityNotFoundError: If the key doesn't exist.
        """
        api_key = await self.repository.get_by_id(key_id)
        if not api_key:
            raise EntityNotFoundError("APIKey", str(key_id))

        api_key.revoke()
        return await self.repository.update(api_key)

    async def record_usage(self, key_id: UUID, used_at: datetime) -> APIKey:
        """Record that an API key was used at a specific time.

        This is typically called automatically during validation, but can
        also be called explicitly if needed.

        Args:
            key_id: The ID of the API key that was used.
            used_at: The timestamp when the key was used.

        Returns:
            The updated APIKey domain entity.

        Raises:
            EntityNotFoundError: If the key doesn't exist.
        """
        api_key = await self.repository.get_by_id(key_id)
        if not api_key:
            raise EntityNotFoundError("APIKey", str(key_id))

        api_key.record_usage(used_at)
        return await self.repository.update(api_key)
