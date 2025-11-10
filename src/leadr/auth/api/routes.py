"""API routes for authentication and API key management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from leadr.auth.api.schemas import (
    APIKeyResponse,
    CreateAPIKeyRequest,
    CreateAPIKeyResponse,
    UpdateAPIKeyRequest,
)
from leadr.auth.domain.api_key import APIKeyStatus
from leadr.auth.services.api_key_service import APIKeyService
from leadr.common.dependencies import DatabaseSession
from leadr.common.domain.models import EntityID

router = APIRouter()


@router.post(
    "",
    response_model=CreateAPIKeyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    request: CreateAPIKeyRequest,
    db: DatabaseSession,
) -> CreateAPIKeyResponse:
    """Create a new API key for an account.

    The plain API key is returned only once in this response.
    Store it securely as it cannot be retrieved later.

    Returns:
        CreateAPIKeyResponse with the plain key included.

    Raises:
        404: Account not found.
    """
    service = APIKeyService(db)
    account_id = EntityID(value=request.account_id)

    try:
        # Create API key
        api_key, plain_key = await service.create_api_key(
            account_id=account_id,
            name=request.name,
            expires_at=request.expires_at,
        )
    except IntegrityError:
        # Foreign key constraint violation - account doesn't exist
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        ) from None

    return CreateAPIKeyResponse.from_domain(api_key, plain_key)


@router.get(
    "",
    response_model=list[APIKeyResponse],
)
async def list_api_keys(
    db: DatabaseSession,
    account_id: Annotated[UUID | None, Query(description="Filter by account ID")] = None,
    status: Annotated[APIKeyStatus | None, Query(description="Filter by status")] = None,
) -> list[APIKeyResponse]:
    """List API keys with optional filters.

    Query parameters can be combined to narrow results.

    Args:
        account_id: Optional account ID to filter results.
        status: Optional status to filter results (active or revoked).

    Returns:
        List of API keys matching the filters.
    """
    service = APIKeyService(db)

    # Get filtered list from service
    api_keys = await service.list_api_keys(
        account_id=EntityID(value=account_id) if account_id else None,
        status=status.value if status else None,
    )

    return [APIKeyResponse.from_domain(key) for key in api_keys]


@router.get(
    "/{key_id}",
    response_model=APIKeyResponse,
)
async def get_api_key(
    key_id: UUID,
    db: DatabaseSession,
) -> APIKeyResponse:
    """Get a single API key by ID.

    Args:
        key_id: The UUID of the API key to retrieve.

    Returns:
        APIKeyResponse with key details (excludes the plain key).

    Raises:
        404: API key not found.
    """
    service = APIKeyService(db)
    api_key = await service.get_by_id_or_raise(EntityID(value=key_id))
    return APIKeyResponse.from_domain(api_key)


@router.patch(
    "/{key_id}",
    response_model=APIKeyResponse,
)
async def update_api_key(
    key_id: UUID,
    request: UpdateAPIKeyRequest,
    db: DatabaseSession,
) -> APIKeyResponse:
    """Update an API key.

    Currently supports:
    - Updating status (e.g., to revoke a key)
    - Soft delete via deleted flag

    Args:
        key_id: The UUID of the API key to update.
        request: Update request with optional status and deleted fields.

    Returns:
        APIKeyResponse with updated key details.

    Raises:
        404: API key not found.
    """
    service = APIKeyService(db)
    entity_id = EntityID(value=key_id)

    # Update status if provided
    if request.status is not None:
        api_key = await service.update_api_key_status(entity_id, request.status.value)
        return APIKeyResponse.from_domain(api_key)

    # Handle soft delete if provided
    if request.deleted is not None and request.deleted:
        api_key = await service.soft_delete(entity_id)
        return APIKeyResponse.from_domain(api_key)

    # No update requested, just fetch current state
    api_key = await service.get_by_id_or_raise(entity_id)
    return APIKeyResponse.from_domain(api_key)
