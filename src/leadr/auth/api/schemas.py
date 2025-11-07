"""API schemas for API Key endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from leadr.auth.domain.api_key import APIKeyStatus


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


class UpdateAPIKeyRequest(BaseModel):
    """Request schema for updating an API key.

    Can update status (e.g., to revoke) or set deleted flag for soft delete.
    """

    status: APIKeyStatus | None = None
    deleted: bool | None = None
