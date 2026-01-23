"""API routes for identity management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from leadr.auth.api.identity_schemas import IdentityResponse, IdentityUpdateRequest
from leadr.auth.dependencies import AdminAuthContextDep
from leadr.auth.domain.identity import IdentityKind
from leadr.auth.services.dependencies import IdentityServiceDep
from leadr.common.api.pagination import PaginatedResponse, PaginationParams
from leadr.common.domain.cursor import CursorValidationError
from leadr.common.domain.ids import AccountID, GameID, IdentityID

router = APIRouter()


@router.get("/identities", response_model=PaginatedResponse[IdentityResponse])
async def list_identities(
    auth: AdminAuthContextDep,
    service: IdentityServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    account_id: Annotated[AccountID | None, Query(description="Account ID filter")] = None,
    game_id: Annotated[GameID | None, Query(description="Filter by game ID")] = None,
    kind: Annotated[str | None, Query(description="Filter by identity kind")] = None,
) -> PaginatedResponse[IdentityResponse]:
    """List identities for an account with optional filters and pagination.

    Returns all non-deleted identities for the specified account, with optional
    filtering by game or kind.

    For regular users, account_id is automatically derived from their API key.
    For superadmins, account_id is optional - if omitted, returns identities from all accounts.

    Pagination:
    - Default: 20 items per page, sorted by created_at:desc,id:asc
    - Custom sort: Use ?sort=display_name:asc,created_at:desc
    - Valid sort fields: id, display_name, kind, created_at, updated_at
    - Navigation: Use next_cursor/prev_cursor from response

    Example:
        GET /v1/identities?account_id=acc_123&game_id=game_456&kind=DEVICE&limit=50

    Args:
        auth: Authentication context with user info.
        service: Injected identity service dependency.
        pagination: Pagination parameters (cursor, limit, sort).
        account_id: Optional account_id query parameter (superadmins can omit to see all).
        game_id: Optional game ID to filter by.
        kind: Optional kind to filter by (DEVICE, STEAM, CUSTOM).

    Returns:
        PaginatedResponse with identities and pagination metadata.

    Raises:
        400: Invalid cursor, sort field, kind, or cursor state mismatch.
        403: User does not have access to the specified account.
    """
    # Superadmin without account_id = None (all accounts)
    # Superadmin with account_id = that specific account
    # Regular user = always their account_id (ignores query param)
    effective_account_id = account_id if auth.is_superadmin else auth.account_id

    # Parse kind if provided
    kind_enum: IdentityKind | None = None
    if kind is not None:
        try:
            kind_enum = IdentityKind(kind)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid kind: {kind}. Must be one of: DEVICE, STEAM, CUSTOM",
            ) from None

    try:
        result = await service.list_identities(
            account_id=effective_account_id,
            game_id=game_id,
            kind=kind_enum,
            pagination=pagination,
        )
    except (CursorValidationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Build filter dict for cursors
    filters_dict: dict[str, str] = {}
    if game_id is not None:
        filters_dict["game_id"] = str(game_id)
    if kind is not None:
        filters_dict["kind"] = kind

    return PaginatedResponse.from_paginated_result(
        result=result,
        pagination=pagination,
        filters=filters_dict,
        response_model=IdentityResponse,
    )


@router.get("/identities/{identity_id}", response_model=IdentityResponse)
async def get_identity(
    identity_id: IdentityID,
    service: IdentityServiceDep,
    auth: AdminAuthContextDep,
) -> IdentityResponse:
    """Get an identity by ID.

    Args:
        identity_id: Identity identifier to retrieve.
        service: Injected identity service dependency.
        auth: Authentication context with user info.

    Returns:
        IdentityResponse with the identity details.

    Raises:
        403: User does not have access to this identity's account.
        404: Identity not found or soft-deleted.
    """
    identity = await service.get_by_id_or_raise(identity_id)

    # Check authorization
    if not auth.has_access_to_account(identity.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this identity's account",
        )

    return IdentityResponse.from_domain(identity)


@router.patch("/identities/{identity_id}", response_model=IdentityResponse)
async def update_identity(
    identity_id: IdentityID,
    request: IdentityUpdateRequest,
    service: IdentityServiceDep,
    auth: AdminAuthContextDep,
) -> IdentityResponse:
    """Update an identity.

    Allows updating display name or soft-deleting the identity.

    Args:
        identity_id: Identity identifier to update.
        request: Update details (display_name, deleted).
        service: Injected identity service dependency.
        auth: Authentication context with user info.

    Returns:
        IdentityResponse with the updated identity details.

    Raises:
        403: User does not have access to this identity's account.
        404: Identity not found.
    """
    # Get the identity to check account access
    identity = await service.get_by_id_or_raise(identity_id)

    # Check authorization
    if not auth.has_access_to_account(identity.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this identity's account",
        )

    # Handle soft delete
    if request.deleted is True:
        identity = await service.soft_delete(identity_id)
        return IdentityResponse.from_domain(identity)

    # Handle display name update
    if request.display_name is not None:
        identity = await service.update_identity(
            identity_id=identity_id,
            display_name=request.display_name,
        )

    return IdentityResponse.from_domain(identity)
