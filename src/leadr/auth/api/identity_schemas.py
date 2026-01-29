"""API request and response models for identities."""

from datetime import datetime

from pydantic import BaseModel, Field

from leadr.auth.domain.identity import Identity, IdentitySession
from leadr.common.domain.ids import AccountID, GameID, IdentityID, IdentitySessionID


class IdentityUpdateRequest(BaseModel):
    """Request model for updating an identity."""

    display_name: str | None = Field(
        default=None,
        description="Updated display name",
    )
    deleted: bool | None = Field(
        default=None,
        description="Set to true to soft-delete the identity",
    )


class IdentityResponse(BaseModel):
    """Response model for an identity."""

    id: IdentityID = Field(description="Unique identifier for the identity")
    account_id: AccountID = Field(description="ID of the account this identity belongs to")
    game_id: GameID = Field(description="ID of the game this identity belongs to")
    kind: str = Field(description="Identity kind: DEVICE, STEAM, or CUSTOM")
    external_key: str = Field(description="External identifier (device ID, Steam ID, etc.)")
    display_name: str | None = Field(default=None, description="Player display name")
    created_at: datetime = Field(description="Timestamp when identity was created (UTC)")
    updated_at: datetime = Field(description="Timestamp of last update (UTC)")

    @classmethod
    def from_domain(cls, identity: Identity) -> "IdentityResponse":
        """Convert domain entity to response model.

        Args:
            identity: The domain Identity entity to convert.

        Returns:
            IdentityResponse with all fields populated from the domain entity.
        """
        return cls(
            id=identity.id,
            account_id=identity.account_id,
            game_id=identity.game_id,
            kind=identity.kind.value,
            external_key=identity.external_key,
            display_name=identity.display_name,
            created_at=identity.created_at,
            updated_at=identity.updated_at,
        )


class IdentitySessionResponse(BaseModel):
    """Response model for an identity session."""

    id: IdentitySessionID = Field(description="Unique identifier for the session")
    identity_id: IdentityID = Field(description="ID of the identity this session belongs to")
    expires_at: datetime = Field(description="Access token expiration time (UTC)")
    refresh_expires_at: datetime = Field(description="Refresh token expiration time (UTC)")
    revoked_at: datetime | None = Field(default=None, description="Time when session was revoked")
    created_at: datetime = Field(description="Timestamp when session was created (UTC)")
    updated_at: datetime = Field(description="Timestamp of last update (UTC)")

    @classmethod
    def from_domain(cls, session: IdentitySession) -> "IdentitySessionResponse":
        """Convert domain entity to response model.

        Args:
            session: The domain IdentitySession entity to convert.

        Returns:
            IdentitySessionResponse with all fields populated from the domain entity.
        """
        return cls(
            id=session.id,
            identity_id=session.identity_id,
            expires_at=session.expires_at,
            refresh_expires_at=session.refresh_expires_at,
            revoked_at=session.revoked_at,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
