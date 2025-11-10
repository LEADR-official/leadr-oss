"""API Key domain model."""

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID

from pydantic import field_validator

from leadr.common.domain.models import Entity


class APIKeyStatus(Enum):
    """API Key status enumeration."""

    ACTIVE = "active"
    REVOKED = "revoked"


class APIKey(Entity):
    """API Key domain entity.

    Represents an API key used to authenticate requests to the admin API.
    Each account can have multiple API keys for different purposes.
    Keys are stored hashed for security and shown only once at creation.
    """

    account_id: UUID
    name: str
    key_hash: str
    key_prefix: str
    status: APIKeyStatus = APIKeyStatus.ACTIVE
    last_used_at: datetime | None = None
    expires_at: datetime | None = None

    @field_validator("key_prefix")
    @classmethod
    def validate_key_prefix(cls, value: str) -> str:
        """Validate that key_prefix starts with 'ldr_'."""
        if not value.startswith("ldr_"):
            raise ValueError("API key prefix must start with 'ldr_'")
        return value

    def revoke(self) -> None:
        """Revoke the API key, preventing further use."""
        self.status = APIKeyStatus.REVOKED

    def is_expired(self) -> bool:
        """Check if the API key has expired.

        Returns:
            True if the key has an expiration date and it's in the past.
        """
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at

    def is_valid(self) -> bool:
        """Check if the API key is valid for use.

        A key is valid if it's active and not expired.

        Returns:
            True if the key can be used for authentication.
        """
        return self.status == APIKeyStatus.ACTIVE and not self.is_expired()

    def record_usage(self, used_at: datetime) -> None:
        """Record that the API key was used.

        Args:
            used_at: Timestamp when the key was used.
        """
        self.last_used_at = used_at
