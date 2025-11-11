"""Device domain models for client authentication."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from leadr.common.domain.models import Entity


class DeviceStatus(Enum):
    """Device status enumeration."""

    ACTIVE = "active"
    BANNED = "banned"
    SUSPENDED = "suspended"


class Device(Entity):
    """Device domain entity.

    Represents a game client device (e.g., mobile device, PC, console).
    Devices are scoped per-game and used for client authentication.
    Each device is identified by a client-generated device_id.
    """

    game_id: UUID
    device_id: str
    account_id: UUID
    platform: str | None = None
    status: DeviceStatus = DeviceStatus.ACTIVE
    first_seen_at: datetime
    last_seen_at: datetime
    metadata: dict[str, Any] = {}

    def is_active(self) -> bool:
        """Check if the device is active.

        Returns:
            True if the device status is ACTIVE.
        """
        return self.status == DeviceStatus.ACTIVE

    def ban(self) -> None:
        """Ban the device, preventing further authentication."""
        self.status = DeviceStatus.BANNED

    def suspend(self) -> None:
        """Suspend the device temporarily."""
        self.status = DeviceStatus.SUSPENDED

    def activate(self) -> None:
        """Activate the device, allowing authentication."""
        self.status = DeviceStatus.ACTIVE

    def update_last_seen(self) -> None:
        """Update the last_seen_at timestamp to current time."""
        self.last_seen_at = datetime.now(UTC)


class DeviceSession(Entity):
    """Device session domain entity.

    Represents an active authentication session for a device.
    Sessions have an expiration time and can be revoked manually.
    """

    device_id: UUID
    access_token_hash: str
    expires_at: datetime
    ip_address: str | None = None
    user_agent: str | None = None
    revoked_at: datetime | None = None

    def is_expired(self) -> bool:
        """Check if the session has expired.

        Returns:
            True if the current time is past the expiration time.
        """
        return datetime.now(UTC) >= self.expires_at

    def is_revoked(self) -> bool:
        """Check if the session has been manually revoked.

        Returns:
            True if revoked_at is set.
        """
        return self.revoked_at is not None

    def is_valid(self) -> bool:
        """Check if the session is valid for use.

        A session is valid if it's not expired and not revoked.

        Returns:
            True if the session can be used for authentication.
        """
        return not self.is_expired() and not self.is_revoked()

    def revoke(self) -> None:
        """Revoke the session, preventing further use."""
        self.revoked_at = datetime.now(UTC)
