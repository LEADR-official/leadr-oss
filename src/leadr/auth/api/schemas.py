"""API schemas for API Key endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from leadr.auth.domain.api_key import APIKey, APIKeyStatus


class CreateAPIKeyRequest(BaseModel):
    """Request schema for creating an API key."""

    account_id: UUID
    name: str
    expires_at: datetime | None = None


class CreateAPIKeyResponse(BaseModel):
    """Response schema for creating an API key.

    Includes the plain API key which is only shown once.
    The client must save this key as it cannot be retrieved later.
    """

    id: UUID
    name: str
    key: str  # Plain API key, only returned once
    prefix: str
    status: APIKeyStatus
    expires_at: datetime | None = None
    created_at: datetime

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
            id=api_key.id.value,
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

    id: UUID
    account_id: UUID
    name: str
    prefix: str
    status: APIKeyStatus
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, api_key: APIKey) -> "APIKeyResponse":
        """Convert domain entity to response model.

        Args:
            api_key: The domain APIKey entity

        Returns:
            APIKeyResponse with all fields populated
        """
        return cls(
            id=api_key.id.value,
            account_id=api_key.account_id.value,
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

    status: APIKeyStatus | None = None
    deleted: bool | None = None
