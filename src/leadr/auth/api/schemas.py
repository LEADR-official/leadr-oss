"""API schemas for Authentication endpoints."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from leadr.auth.domain.api_key import APIKey, APIKeyStatus
from leadr.auth.domain.device import Device, DeviceStatus
from leadr.common.domain.ids import (
    AccountID,
    APIKeyID,
    DeviceID,
    GameID,
    UserID,
)


class CreateAPIKeyRequest(BaseModel):
    """Request schema for creating an API key."""

    account_id: AccountID = Field(description="ID of the account this API key belongs to")
    user_id: UserID = Field(description="ID of the user who owns this API key")
    name: str = Field(description="Human-readable name for the API key (e.g., 'Production Server')")
    expires_at: datetime | None = Field(
        default=None,
        description="Optional expiration timestamp (UTC). Key never expires if omitted",
    )


class CreateAPIKeyResponse(BaseModel):
    """Response schema for creating an API key.

    Includes the plain API key which is only shown once.
    The client must save this key as it cannot be retrieved later.
    """

    id: APIKeyID = Field(description="Unique identifier for the API key")
    name: str = Field(description="Human-readable name for the API key")
    key: str = Field(
        description="Plain text API key. ONLY returned at creation - save this securely!"
    )
    prefix: str = Field(description="Key prefix for identification (first 8 characters)")
    status: APIKeyStatus = Field(description="Current status of the API key")
    expires_at: datetime | None = Field(
        default=None, description="Expiration timestamp (UTC), or null if never expires"
    )
    created_at: datetime = Field(description="Timestamp when the key was created (UTC)")

    @classmethod
    def from_domain(cls, api_key: APIKey, plain_key: str) -> "CreateAPIKeyResponse":
        """Convert domain entity to response model with plain key.

        Args:
            api_key: The domain APIKey entity
            plain_key: The plain text API key (only available at creation)

        Returns:
            CreateAPIKeyResponse with all fields populated
        """
        return cls(
            id=api_key.id,
            name=api_key.name,
            key=plain_key,
            prefix=api_key.key_prefix,
            status=api_key.status,
            expires_at=api_key.expires_at,
            created_at=api_key.created_at,
        )


class APIKeyResponse(BaseModel):
    """Response schema for API key details.

    Excludes sensitive information like key_hash.
    The full key is never returned after creation.
    """

    model_config = ConfigDict(extra="forbid")

    id: APIKeyID = Field(description="Unique identifier for the API key")
    account_id: AccountID = Field(description="ID of the account this key belongs to")
    user_id: UserID = Field(description="ID of the user who owns this API key")
    name: str = Field(description="Human-readable name for the API key")
    prefix: str = Field(description="Key prefix for identification (first 8 characters)")
    status: APIKeyStatus = Field(description="Current status (active, revoked, expired)")
    last_used_at: datetime | None = Field(
        default=None, description="Timestamp of last successful authentication (UTC)"
    )
    expires_at: datetime | None = Field(
        default=None, description="Expiration timestamp (UTC), or null if never expires"
    )
    created_at: datetime = Field(description="Timestamp when the key was created (UTC)")
    updated_at: datetime = Field(description="Timestamp of last update (UTC)")

    @classmethod
    def from_domain(cls, api_key: APIKey) -> "APIKeyResponse":
        """Convert domain entity to response model.

        Args:
            api_key: The domain APIKey entity

        Returns:
            APIKeyResponse with all fields populated
        """
        return cls(
            id=api_key.id,
            account_id=api_key.account_id,
            user_id=api_key.user_id,
            name=api_key.name,
            prefix=api_key.key_prefix,
            status=api_key.status,
            last_used_at=api_key.last_used_at,
            expires_at=api_key.expires_at,
            created_at=api_key.created_at,
            updated_at=api_key.updated_at,
        )


class UpdateAPIKeyRequest(BaseModel):
    """Request schema for updating an API key.

    Can update status (e.g., to revoke) or set deleted flag for soft delete.
    """

    status: APIKeyStatus | None = Field(
        default=None, description="Updated status (use 'revoked' to disable key)"
    )
    deleted: bool | None = Field(default=None, description="Set to true to soft delete the key")


# Client Session Schemas


class StartSessionRequest(BaseModel):
    """Request schema for starting a device session.

    Used by game clients to authenticate and obtain an access token.
    """

    game_id: GameID = Field(description="ID of the game this device belongs to")
    device_id: str = Field(
        description="Client-generated unique device identifier (e.g., UUID, hardware ID)"
    )
    platform: str | None = Field(
        default=None, description="Device platform (e.g., 'ios', 'android', 'pc', 'console')"
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Optional device metadata (e.g., OS version, device model)"
    )


class StartSessionResponse(BaseModel):
    """Response schema for starting a device session.

    Includes both access and refresh tokens which must be saved by the client.
    - Access token: Short-lived, used for API requests in Authorization header
    - Refresh token: Long-lived, used to obtain new access tokens when expired
    """

    id: DeviceID = Field(description="Unique identifier for the device")
    game_id: GameID = Field(description="ID of the game")
    device_id: str = Field(description="Client-generated device identifier")
    account_id: AccountID = Field(description="ID of the account that owns the game")
    platform: str | None = Field(default=None, description="Device platform")
    status: DeviceStatus = Field(description="Device status (active, suspended, banned)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Device metadata")
    access_token: str = Field(description="JWT access token for authenticating API requests")
    refresh_token: str = Field(description="JWT refresh token for obtaining new access tokens")
    expires_in: int = Field(description="Access token expiration time in seconds")
    first_seen_at: datetime = Field(description="Timestamp when device was first seen (UTC)")
    last_seen_at: datetime = Field(description="Timestamp when device was last seen (UTC)")

    @classmethod
    def from_domain(
        cls, device: Device, access_token: str, refresh_token: str, expires_in: int
    ) -> "StartSessionResponse":
        """Convert domain entity to response model with tokens.

        Args:
            device: The domain Device entity
            access_token: The plain JWT access token
            refresh_token: The plain JWT refresh token
            expires_in: Access token expiration time in seconds

        Returns:
            StartSessionResponse with all fields populated
        """
        return cls(
            id=device.id,
            game_id=device.game_id,
            device_id=device.device_id,
            account_id=device.account_id,
            platform=device.platform,
            status=device.status,
            metadata=device.metadata,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            first_seen_at=device.first_seen_at,
            last_seen_at=device.last_seen_at,
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
