"""Nonce service for managing request nonces."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.auth.domain.nonce import Nonce, NonceStatus
from leadr.auth.services.repositories import NonceRepository
from leadr.common.services import BaseService


class NonceService(BaseService[Nonce, NonceRepository]):
    """Service for managing request nonces.

    Nonces are single-use tokens that clients must obtain before making
    mutating requests. This prevents replay attacks by ensuring each
    request is fresh and authorized by the server.
    """

    def _create_repository(self, session: AsyncSession) -> NonceRepository:
        """Create nonce repository."""
        return NonceRepository(session)

    def _get_entity_name(self) -> str:
        """Get entity name for error messages."""
        return "Nonce"

    async def generate_nonce(
        self,
        device_id: UUID,
        ttl_seconds: int = 60,
    ) -> tuple[str, datetime]:
        """Generate a fresh nonce for a device.

        Args:
            device_id: Device ID to associate nonce with
            ttl_seconds: Time-to-live in seconds (default 60)

        Returns:
            tuple[str, datetime]: (nonce_value, expires_at)

        Example:
            >>> nonce_value, expires_at = await service.generate_nonce(device_id)
            >>> # Client includes nonce_value in leadr-client-nonce header
        """
        nonce_value = str(uuid4())
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)

        nonce = Nonce(
            device_id=device_id,
            nonce_value=nonce_value,
            expires_at=expires_at,
            status=NonceStatus.PENDING,
        )

        await self.repository.create(nonce)

        return nonce_value, expires_at

    async def validate_and_consume_nonce(
        self,
        nonce_value: str,
        device_id: UUID,
    ) -> bool:
        """Validate nonce and mark as used (atomic operation).

        Args:
            nonce_value: The nonce value to validate
            device_id: Expected device ID (must match nonce owner)

        Returns:
            True if nonce was valid and consumed

        Raises:
            ValueError: If nonce is invalid (expired, already used, wrong device, or not found)

        Example:
            >>> try:
            ...     await service.validate_and_consume_nonce(nonce_value, device.id)
            ... except ValueError as e:
            ...     # Handle invalid nonce (return 412 error to client)
            ...     raise HTTPException(status_code=412, detail=str(e))
        """
        nonce = await self.repository.get_by_nonce_value(nonce_value)

        if nonce is None:
            raise ValueError("Nonce not found")

        if nonce.device_id != device_id:
            raise ValueError("Nonce does not belong to this device")

        if nonce.is_used():
            raise ValueError("Nonce already used")

        if nonce.is_expired():
            raise ValueError("Nonce expired")

        # Mark as used atomically
        nonce.mark_used()
        await self.repository.update(nonce)

        return True

    async def cleanup_expired_nonces(self, older_than_hours: int = 24) -> int:
        """Clean up expired nonces older than specified hours.

        Only deletes nonces with PENDING status. Used nonces are kept
        for audit/debugging purposes.

        Args:
            older_than_hours: Delete nonces expired before this many hours ago (default 24)

        Returns:
            Number of nonces deleted

        Example:
            >>> # In background task or cron job
            >>> deleted = await service.cleanup_expired_nonces(older_than_hours=24)
            >>> logger.info(f"Cleaned up {deleted} expired nonces")
        """
        cutoff = datetime.now(UTC) - timedelta(hours=older_than_hours)
        return await self.repository.cleanup_expired_nonces(cutoff)
