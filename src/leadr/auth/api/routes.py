"""API routes for authentication and API key management."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import UUID4
from sqlalchemy.exc import IntegrityError

from leadr.auth.api.schemas import (
    APIKeyResponse,
    CreateAPIKeyRequest,
    CreateAPIKeyResponse,
    UpdateAPIKeyRequest,
)
from leadr.auth.dependencies import AuthContextDep
from leadr.auth.domain.api_key import APIKeyStatus
from leadr.auth.services.dependencies import APIKeyServiceDep

router = APIRouter()


@router.post(
    "/api-keys",
    response_model=CreateAPIKeyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    request: CreateAPIKeyRequest,
    service: APIKeyServiceDep,
    auth: AuthContextDep,
) -> CreateAPIKeyResponse:
    """Create a new API key for an account.

    The plain API key is returned only once in this response.
    Store it securely as it cannot be retrieved later.

    Returns:
        CreateAPIKeyResponse with the plain key included.

    Raises:
        403: User does not have access to this account.
        404: Account not found.
    """
    # Check authorization
    if not auth.has_access_to_account(request.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this account",
        )

    try:
        # Create API key
        api_key, plain_key = await service.create_api_key(
            account_id=request.account_id,
            user_id=request.user_id,
            name=request.name,
            expires_at=request.expires_at,
        )
    except IntegrityError:
        # Foreign key constraint violation - account or user doesn't exist
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account or user not found",
        ) from None

    return CreateAPIKeyResponse.from_domain(api_key, plain_key)


@router.get(
    "/api-keys",
    response_model=list[APIKeyResponse],
)
async def list_api_keys(
    service: APIKeyServiceDep,
    auth: AuthContextDep,
    account_id: Annotated[UUID4, Query(description="Account ID to filter by")],
    key_status: Annotated[
        APIKeyStatus | None, Query(alias="status", description="Filter by status")
    ] = None,
) -> list[APIKeyResponse]:
    """List API keys for an account with optional filters.

    Args:
        service: Injected API key service dependency.
        auth: Authentication context with user info.
        account_id: Account ID to filter results (REQUIRED for multi-tenant safety).
        key_status: Optional status to filter results (active or revoked).

    Returns:
        List of API keys matching the filters.

    Raises:
        403: User does not have access to this account.
    """
    # Check authorization
    if not auth.has_access_to_account(account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this account",
        )

    # Get filtered list from service
    api_keys = await service.list_api_keys(
        account_id=account_id,
        status=key_status.value if key_status else None,
    )

    return [APIKeyResponse.from_domain(key) for key in api_keys]


@router.get(
    "/api-keys/{key_id}",
    response_model=APIKeyResponse,
)
async def get_api_key(
    key_id: UUID4,
    service: APIKeyServiceDep,
    auth: AuthContextDep,
) -> APIKeyResponse:
    """Get a single API key by ID.

    Args:
        key_id: The UUID of the API key to retrieve.
        service: Injected API key service dependency.
        auth: Authentication context with user info.

    Returns:
        APIKeyResponse with key details (excludes the plain key).

    Raises:
        403: User does not have access to this API key's account.
        404: API key not found.
    """
    api_key = await service.get_by_id_or_raise(key_id)

    # Check authorization
    if not auth.has_access_to_account(api_key.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this API key's account",
        )

    return APIKeyResponse.from_domain(api_key)


@router.patch(
    "/api-keys/{key_id}",
    response_model=APIKeyResponse,
)
async def update_api_key(
    key_id: UUID4,
    request: UpdateAPIKeyRequest,
    service: APIKeyServiceDep,
    auth: AuthContextDep,
) -> APIKeyResponse:
    """Update an API key.

    Currently supports:
    - Updating status (e.g., to revoke a key)
    - Soft delete via deleted flag

    Args:
        key_id: The UUID of the API key to update.
        request: Update request with optional status and deleted fields.
        service: Injected API key service dependency.
        auth: Authentication context with user info.

    Returns:
        APIKeyResponse with updated key details.

    Raises:
        403: User does not have access to this API key's account.
        404: API key not found.
    """
    # Fetch key to check authorization
    api_key = await service.get_by_id_or_raise(key_id)

    # Check authorization
    if not auth.has_access_to_account(api_key.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this API key's account",
        )

    # Update status if provided
    if request.status is not None:
        api_key = await service.update_api_key_status(key_id, request.status.value)
        return APIKeyResponse.from_domain(api_key)

    # Handle soft delete if provided
    if request.deleted is not None and request.deleted:
        api_key = await service.soft_delete(key_id)
        return APIKeyResponse.from_domain(api_key)

    # No update requested, just return current state
    return APIKeyResponse.from_domain(api_key)
