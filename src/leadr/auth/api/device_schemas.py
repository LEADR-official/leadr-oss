"""API request and response models for devices."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from leadr.auth.domain.device import Device
from leadr.common.domain.ids import AccountID, DeviceID, GameID


class DeviceUpdateRequest(BaseModel):
    """Request model for updating a device."""

    status: str | None = Field(
        default=None,
        description="Updated status: active, banned, or suspended",
    )


class DeviceResponse(BaseModel):
    """Response model for a device."""

    id: DeviceID = Field(description="Unique identifier for the device")
    game_id: GameID = Field(description="ID of the game this device belongs to")
    device_id: str = Field(description="Client-generated device identifier")
    account_id: AccountID = Field(description="ID of the account this device belongs to")
    platform: str | None = Field(default=None, description="Platform (iOS, Android, etc.), or null")
    status: str = Field(description="Device status: active, banned, or suspended")
    first_seen_at: datetime = Field(description="Timestamp when device was first seen (UTC)")
    last_seen_at: datetime = Field(description="Timestamp when device was last seen (UTC)")
    metadata: dict[str, Any] = Field(description="Additional device metadata")
    created_at: datetime = Field(description="Timestamp when device record was created (UTC)")
    updated_at: datetime = Field(description="Timestamp of last update (UTC)")

    @classmethod
    def from_domain(cls, device: Device) -> "DeviceResponse":
        """Convert domain entity to response model.

        Args:
            device: The domain Device entity to convert.

        Returns:
            DeviceResponse with all fields populated from the domain entity.
        """
        return cls(
            id=device.id,
            game_id=device.game_id,
            device_id=device.device_id,
            account_id=device.account_id,
            platform=device.platform,
            status=device.status.value,
            first_seen_at=device.first_seen_at,
            last_seen_at=device.last_seen_at,
            metadata=device.metadata,
            created_at=device.created_at,
            updated_at=device.updated_at,
        )
