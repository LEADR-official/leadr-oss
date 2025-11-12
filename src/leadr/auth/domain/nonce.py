"""Nonce domain entity for replay protection."""

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID

from pydantic import Field

from leadr.common.domain.models import Entity


class NonceStatus(str, Enum):
    """Nonce status enumeration."""

    PENDING = "pending"  # Issued but not yet used
    USED = "used"  # Successfully consumed
    EXPIRED = "expired"  # Never used and now expired


class Nonce(Entity):
    """Request nonce for replay protection.

    Nonces are single-use tokens that clients must obtain before making
    mutating requests (POST, PATCH, DELETE). Each nonce has a short TTL
    (typically 60 seconds) and can only be used once.

    This prevents replay attacks by ensuring that each mutating request
    is fresh and authorized by the server.
    """

    device_id: UUID = Field(description="Device that owns this nonce")
    nonce_value: str = Field(description="Unique nonce value (UUID string)")
    expires_at: datetime = Field(description="Nonce expiration timestamp")
    used_at: datetime | None = Field(default=None, description="When nonce was consumed")
    status: NonceStatus = Field(default=NonceStatus.PENDING, description="Nonce status")

    def is_expired(self) -> bool:
        """Check if nonce has expired.

        Returns:
            True if current time is at or past expires_at
        """
        return datetime.now(UTC) >= self.expires_at

    def is_used(self) -> bool:
        """Check if nonce has been used.

        Returns:
            True if status is USED
        """
        return self.status == NonceStatus.USED

    def is_valid(self) -> bool:
        """Check if nonce is valid (not used and not expired).

        Returns:
            True if nonce is pending and not expired
        """
        return self.status == NonceStatus.PENDING and not self.is_expired()

    def mark_used(self) -> None:
        """Mark nonce as used.

        Sets status to USED and records used_at timestamp.

        Raises:
            ValueError: If nonce is not valid (already used or expired)
        """
        if not self.is_valid():
            raise ValueError("Cannot mark invalid nonce as used")

        self.status = NonceStatus.USED
        self.used_at = datetime.now(UTC)

    def mark_expired(self) -> None:
        """Mark nonce as expired.

        Only marks nonce as expired if it's currently pending.
        Does not change status if already used or expired.
        """
        if self.status == NonceStatus.PENDING:
            self.status = NonceStatus.EXPIRED
