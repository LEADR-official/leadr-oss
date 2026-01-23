"""Identity domain models for player identification."""

from datetime import UTC, datetime
from enum import Enum

from pydantic import Field

from leadr.common.domain.ids import AccountID, GameID, IdentityID, IdentitySessionID
from leadr.common.domain.models import Entity


class IdentityKind(str, Enum):
    """Identity provider type enumeration."""

    DEVICE = "DEVICE"
    STEAM = "STEAM"
    CUSTOM = "CUSTOM"


class Identity(Entity):
    """Identity domain entity.

    Represents a player identity within a game. Identities are the ranking key
    for leaderboards, decoupling player identity from specific authentication
    mechanisms (devices, Steam accounts, etc.).

    Each identity is scoped to an account and game, and is uniquely identified
    by the combination of kind and external_key.
    """

    id: IdentityID = Field(
        frozen=True,
        default_factory=IdentityID,
        description="Unique identity identifier",
    )
    account_id: AccountID = Field(frozen=True, description="Account this identity belongs to")
    game_id: GameID = Field(frozen=True, description="Game this identity belongs to")
    kind: IdentityKind = Field(description="Type of identity provider")
    external_key: str = Field(
        description="External identifier (e.g., device ID, Steam ID, custom user ID)"
    )
    display_name: str | None = Field(default=None, description="Player display name")

    def update_display_name(self, name: str | None) -> None:
        """Update the display name.

        Args:
            name: New display name, or None to clear.
        """
        self.display_name = name


class IdentitySession(Entity):
    """Identity session domain entity.

    Represents an active authentication session for an identity.
    Sessions have an expiration time and can be revoked manually.
    Includes both access and refresh tokens with token rotation support.

    Replaces DeviceSession with identity-based authentication.
    """

    id: IdentitySessionID = Field(
        frozen=True,
        default_factory=IdentitySessionID,
        description="Unique identity session identifier",
    )
    identity_id: IdentityID = Field(frozen=True, description="Identity this session belongs to")
    access_token_hash: str
    refresh_token_hash: str
    token_version: int = 1
    expires_at: datetime
    refresh_expires_at: datetime
    ip_address: str | None = None
    user_agent: str | None = None
    revoked_at: datetime | None = None

    def is_expired(self) -> bool:
        """Check if the access token has expired.

        Returns:
            True if the current time is past the expiration time.
        """
        return datetime.now(UTC) >= self.expires_at

    def is_refresh_expired(self) -> bool:
        """Check if the refresh token has expired.

        Returns:
            True if the current time is past the refresh expiration time.
        """
        return datetime.now(UTC) >= self.refresh_expires_at

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

    def rotate_tokens(self) -> None:
        """Increment token version for token rotation.

        Called when refreshing tokens to invalidate old refresh tokens.
        """
        self.token_version += 1
