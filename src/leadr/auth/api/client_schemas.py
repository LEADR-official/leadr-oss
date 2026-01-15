"""API request and response models for client authentication."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from leadr.auth.domain.device import Device, DeviceStatus
from leadr.common.domain.ids import AccountID, DeviceID, GameID


class StartSessionRequest(BaseModel):
    """Request schema for starting a device session.

    Used by game clients to authenticate and obtain an access token.
    """

    game_id: GameID = Field(description="ID of the game this device belongs to")
    client_fingerprint: str = Field(
        description="Client-generated SHA256 device fingerprint (64 hex characters)"
    )
    platform: str | None = Field(
        default=None, description="Device platform (e.g., 'ios', 'android', 'pc', 'console')"
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Optional device metadata (e.g., OS version, device model)"
    )
    test_mode: bool = Field(
        default=False,
        description="If true, session is in test mode and scores will be marked as test",
    )


class StartSessionResponse(BaseModel):
    """Response schema for starting a device session.

    Includes both access and refresh tokens which must be saved by the client.
    - Access token: Short-lived, used for API requests in Authorization header
    - Refresh token: Long-lived, used to obtain new access tokens when expired
    """

    id: DeviceID = Field(description="Unique identifier for the device")
    game_id: GameID = Field(description="ID of the game")
    client_fingerprint: str = Field(
        description="Client-generated SHA256 device fingerprint (64 hex characters)"
    )
    account_id: AccountID = Field(description="ID of the account that owns the game")
    platform: str | None = Field(default=None, description="Device platform")
    status: DeviceStatus = Field(description="Device status (active, suspended, banned)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Device metadata")
    access_token: str = Field(description="JWT access token for authenticating API requests")
    refresh_token: str = Field(description="JWT refresh token for obtaining new access tokens")
    expires_in: int = Field(description="Access token expiration time in seconds")
    first_seen_at: datetime = Field(description="Timestamp when device was first seen (UTC)")
    last_seen_at: datetime = Field(description="Timestamp when device was last seen (UTC)")
    test_mode: bool = Field(description="Whether session is in test mode")

    @classmethod
    def from_domain(
        cls,
        device: Device,
        access_token: str,
        refresh_token: str,
        expires_in: int,
        test_mode: bool = False,
    ) -> "StartSessionResponse":
        """Convert domain entity to response model with tokens.

        Args:
            device: The domain Device entity
            access_token: The plain JWT access token
            refresh_token: The plain JWT refresh token
            expires_in: Access token expiration time in seconds
            test_mode: Whether session is in test mode

        Returns:
            StartSessionResponse with all fields populated
        """
        return cls(
            id=device.id,
            game_id=device.game_id,
            client_fingerprint=device.client_fingerprint,
            account_id=device.account_id,
            platform=device.platform,
            status=device.status,
            metadata=device.metadata,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            first_seen_at=device.first_seen_at,
            last_seen_at=device.last_seen_at,
            test_mode=test_mode,
        )


class RefreshTokenRequest(BaseModel):
    """Request schema for refreshing an access token.

    Used by clients when their access token has expired.
    """

    refresh_token: str = Field(description="JWT refresh token obtained from start_session")


class RefreshTokenResponse(BaseModel):
    """Response schema for token refresh.

    Returns new access and refresh tokens with incremented version.
    The old refresh token is invalidated and cannot be reused.
    """

    access_token: str = Field(description="New JWT access token")
    refresh_token: str = Field(description="New JWT refresh token (old token is invalidated)")
    expires_in: int = Field(description="Access token expiration time in seconds")


class NonceResponse(BaseModel):
    """Response schema for nonce generation.

    Nonces are single-use tokens with short TTL (60 seconds) that clients must
    obtain before making mutating requests. This prevents replay attacks.
    """

    nonce_value: str = Field(description="Unique nonce value (UUID)")
    expires_at: datetime = Field(description="Nonce expiration timestamp (UTC)")
