"""API request and response models for client authentication."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from leadr.auth.domain.identity import Identity, IdentityKind
from leadr.common.domain.ids import AccountID, GameID, IdentityID


class StartSessionRequest(BaseModel):
    """Request schema for starting a device session.

    Used by game clients to authenticate and obtain an access token.
    """

    game_id: GameID = Field(description="ID of the game this device belongs to")
    client_fingerprint: str = Field(
        pattern=r"^[a-fA-F0-9]{64}$",
        description="Client-generated SHA256 device fingerprint (64 hex characters)",
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
    """Response schema for starting an identity session.

    Includes both access and refresh tokens which must be saved by the client.
    - Access token: Short-lived, used for API requests in Authorization header
    - Refresh token: Long-lived, used to obtain new access tokens when expired
    """

    identity_id: IdentityID = Field(description="Unique identifier for the player identity")
    game_id: GameID = Field(description="ID of the game")
    account_id: AccountID = Field(description="ID of the account that owns the game")
    kind: IdentityKind = Field(description="Identity type (DEVICE, STEAM, CUSTOM)")
    display_name: str | None = Field(default=None, description="Player display name")
    access_token: str = Field(description="JWT access token for authenticating API requests")
    refresh_token: str = Field(description="JWT refresh token for obtaining new access tokens")
    expires_in: int = Field(description="Access token expiration time in seconds")
    test_mode: bool = Field(description="Whether session is in test mode")

    @classmethod
    def from_domain(
        cls,
        identity: Identity,
        access_token: str,
        refresh_token: str,
        expires_in: int,
        test_mode: bool = False,
    ) -> "StartSessionResponse":
        """Convert domain entity to response model with tokens.

        Args:
            identity: The domain Identity entity
            access_token: The plain JWT access token
            refresh_token: The plain JWT refresh token
            expires_in: Access token expiration time in seconds
            test_mode: Whether session is in test mode

        Returns:
            StartSessionResponse with all fields populated
        """
        return cls(
            identity_id=identity.id,
            game_id=identity.game_id,
            account_id=identity.account_id,
            kind=identity.kind,
            display_name=identity.display_name,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
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
