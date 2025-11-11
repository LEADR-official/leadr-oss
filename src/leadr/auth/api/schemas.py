"""API schemas for API Key endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from leadr.auth.domain.api_key import APIKey, APIKeyStatus


class CreateAPIKeyRequest(BaseModel):
    """Request schema for creating an API key."""

    account_id: UUID = Field(description="ID of the account this API key belongs to")
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

    id: UUID = Field(description="Unique identifier for the API key")
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

    id: UUID = Field(description="Unique identifier for the API key")
    account_id: UUID = Field(description="ID of the account this key belongs to")
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
