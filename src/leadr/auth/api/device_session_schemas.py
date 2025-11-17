"""API schemas for device sessions."""

from datetime import datetime

from pydantic import BaseModel

from leadr.auth.domain.device import DeviceSession
from leadr.common.domain.ids import DeviceID, DeviceSessionID


class DeviceSessionResponse(BaseModel):
    """Response model for device session."""

    id: DeviceSessionID
    device_id: DeviceID
    expires_at: datetime
    refresh_expires_at: datetime
    ip_address: str | None
    user_agent: str | None
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, session: DeviceSession) -> "DeviceSessionResponse":
        """Convert domain entity to API response."""
        return cls(
            id=session.id,
            device_id=session.device_id,
            expires_at=session.expires_at,
            refresh_expires_at=session.refresh_expires_at,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            revoked_at=session.revoked_at,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )


class DeviceSessionUpdateRequest(BaseModel):
    """Request model for updating device session."""

    revoked: bool | None = None
