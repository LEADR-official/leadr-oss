"""Device domain models for client authentication."""

import re
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from leadr.common.domain.ids import AccountID, DeviceID, GameID
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
    Each device is identified by a client-generated SHA256 fingerprint.
    """

    id: DeviceID = Field(
        frozen=True,
        default_factory=DeviceID,
        description="Unique device identifier",
    )
    game_id: GameID
    client_fingerprint: str = Field(
        description="Client-generated SHA256 device fingerprint (64 hex characters)"
    )
    account_id: AccountID
    platform: str | None = None
    status: DeviceStatus = DeviceStatus.ACTIVE
    first_seen_at: datetime
    last_seen_at: datetime
    metadata: dict[str, Any] = {}

    @field_validator("client_fingerprint")
    @classmethod
    def validate_sha256(cls, v: str) -> str:
        """Validate that client_fingerprint is a valid SHA256 hash.

        Args:
            v: The client_fingerprint value to validate.

        Returns:
            The normalized (lowercase) client_fingerprint.

        Raises:
            ValueError: If the fingerprint is not a valid 64-character hex string.
        """
        if not re.match(r"^[a-f0-9]{64}$", v.lower()):
            raise ValueError("client_fingerprint must be a 64-character SHA256 hash (hex)")
        return v.lower()  # Normalize to lowercase

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
