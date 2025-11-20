"""API routes for authentication and API key management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from leadr.auth.api.api_key_schemas import (
    APIKeyResponse,
    CreateAPIKeyRequest,
    CreateAPIKeyResponse,
    UpdateAPIKeyRequest,
)
from leadr.auth.dependencies import AdminAuthContextDep, AdminAuthContextWithAccountIDDep
from leadr.auth.domain.api_key import APIKeyStatus
from leadr.auth.services.dependencies import APIKeyServiceDep
from leadr.common.api.pagination import PaginatedResponse, PaginationParams
from leadr.common.domain.cursor import CursorValidationError
from leadr.common.domain.ids import AccountID, APIKeyID

router = APIRouter()


@router.post(
    "/api-keys",
    response_model=CreateAPIKeyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    request: CreateAPIKeyRequest,
    service: APIKeyServiceDep,
    auth: AdminAuthContextDep,
) -> CreateAPIKeyResponse:
    """Create a new API key for an account.

    The plain API key is returned only once in this response.
    Store it securely as it cannot be retrieved later.

    For regular users, account_id must match their API key's account.
    For superadmins, any account_id is accepted.

    Returns:
        CreateAPIKeyResponse with the plain key included.

    Raises:
        403: User does not have access to the specified account.
        404: Account not found.
    """
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
    response_model=PaginatedResponse[APIKeyResponse],
)
async def list_api_keys(
    auth: AdminAuthContextWithAccountIDDep,
    service: APIKeyServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    account_id: Annotated[AccountID | None, Query(description="Account ID filter")] = None,
    key_status: Annotated[
        APIKeyStatus | None, Query(alias="status", description="Filter by status")
    ] = None,
) -> PaginatedResponse[APIKeyResponse]:
    """List API keys for an account with optional filters and pagination.

    For regular users, account_id is automatically derived from their API key.
    For superadmins, account_id must be explicitly provided as a query parameter.

    Pagination:
    - Default: 20 items per page, sorted by created_at:desc,id:asc
    - Custom sort: Use ?sort=name:asc,created_at:desc
    - Valid sort fields: id, name, created_at, updated_at
    - Navigation: Use next_cursor/prev_cursor from response

    Example:
        GET /v1/api-keys?account_id=acc_123&status=active&limit=50&sort=name:asc

    Args:
        auth: Authentication context with user info.
        service: Injected API key service dependency.
        pagination: Pagination parameters (cursor, limit, sort).
        account_id: Optional account_id query parameter (required for superadmins).
        key_status: Optional status to filter results (active or revoked).

    Returns:
        PaginatedResponse with API keys and pagination metadata.

    Raises:
        400: Invalid cursor, sort field, or cursor state mismatch.
        400: Superadmin did not provide account_id.
        403: User does not have access to the specified account.
    """
    try:
        result = await service.list_api_keys(
            account_id=account_id or auth.account_id,
            status=key_status.value if key_status else None,
            pagination=pagination,
        )
    except (CursorValidationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Build filter dict for cursors
    filters_dict = {}
    if key_status is not None:
        filters_dict["status"] = key_status.value

    return PaginatedResponse.from_paginated_result(
        result=result,
        pagination=pagination,
        filters=filters_dict,
        response_model=APIKeyResponse,
    )


@router.get(
    "/api-keys/{key_id}",
    response_model=APIKeyResponse,
)
async def get_api_key(
    key_id: APIKeyID,
    service: APIKeyServiceDep,
    auth: AdminAuthContextDep,
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
    key_id: APIKeyID,
    request: UpdateAPIKeyRequest,
    service: APIKeyServiceDep,
    auth: AdminAuthContextDep,
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
