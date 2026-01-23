"""API routes for identity session management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from leadr.auth.api.identity_schemas import IdentitySessionResponse
from leadr.auth.dependencies import AdminAuthContextDep
from leadr.auth.services.dependencies import IdentityServiceDep
from leadr.common.api.pagination import PaginatedResponse, PaginationParams
from leadr.common.domain.cursor import CursorValidationError
from leadr.common.domain.ids import AccountID, IdentityID, IdentitySessionID

router = APIRouter()


@router.get("/identity-sessions", response_model=PaginatedResponse[IdentitySessionResponse])
async def list_identity_sessions(
    auth: AdminAuthContextDep,
    service: IdentityServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    account_id: Annotated[AccountID | None, Query(description="Account ID filter")] = None,
    identity_id: Annotated[IdentityID | None, Query(description="Filter by identity ID")] = None,
) -> PaginatedResponse[IdentitySessionResponse]:
    """List identity sessions with optional filters and pagination.

    Returns all non-deleted sessions, with optional filtering by account or identity.

    For regular users, account_id is automatically derived from their API key.
    For superadmins, account_id is optional - if omitted, returns sessions from all accounts.

    Pagination:
    - Default: 20 items per page, sorted by created_at:desc,id:asc
    - Custom sort: Use ?sort=created_at:desc
    - Valid sort fields: id, created_at, updated_at
    - Navigation: Use next_cursor/prev_cursor from response

    Example:
        GET /v1/identity-sessions?account_id=acc_123&identity_id=ide_456&limit=50

    Args:
        auth: Authentication context with user info.
        service: Injected identity service dependency.
        pagination: Pagination parameters (cursor, limit, sort).
        account_id: Optional account_id query parameter (superadmins can omit to see all).
        identity_id: Optional identity ID to filter by.

    Returns:
        PaginatedResponse with sessions and pagination metadata.

    Raises:
        400: Invalid cursor, sort field, or cursor state mismatch.
        403: User does not have access to the specified account.
    """
    # Superadmin without account_id = None (all accounts)
    # Superadmin with account_id = that specific account
    # Regular user = always their account_id (ignores query param)
    effective_account_id = account_id if auth.is_superadmin else auth.account_id

    try:
        result = await service.list_sessions(
            account_id=effective_account_id,
            identity_id=identity_id,
            pagination=pagination,
        )
    except (CursorValidationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Build filter dict for cursors
    filters_dict: dict[str, str] = {}
    if identity_id is not None:
        filters_dict["identity_id"] = str(identity_id)

    return PaginatedResponse.from_paginated_result(
        result=result,
        pagination=pagination,
        filters=filters_dict,
        response_model=IdentitySessionResponse,
    )


@router.get(
    "/identity-sessions/{session_id}",
    response_model=IdentitySessionResponse,
)
async def get_identity_session(
    session_id: IdentitySessionID,
    service: IdentityServiceDep,
    auth: AdminAuthContextDep,
) -> IdentitySessionResponse:
    """Get an identity session by ID.

    Args:
        session_id: Session identifier to retrieve.
        service: Injected identity service dependency.
        auth: Authentication context with user info.

    Returns:
        IdentitySessionResponse with the session details.

    Raises:
        403: User does not have access to this session's account.
        404: Session not found or soft-deleted.
    """
    session = await service.get_session_or_raise(session_id)

    # Get identity to check account access
    identity = await service.get_by_id_or_raise(session.identity_id)

    # Check authorization
    if not auth.has_access_to_account(identity.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this session's account",
        )

    return IdentitySessionResponse.from_domain(session)


@router.delete(
    "/identity-sessions/{session_id}",
    response_model=IdentitySessionResponse,
)
async def revoke_identity_session(
    session_id: IdentitySessionID,
    service: IdentityServiceDep,
    auth: AdminAuthContextDep,
) -> IdentitySessionResponse:
    """Revoke an identity session.

    Marks the session as revoked, preventing further use.

    Args:
        session_id: Session identifier to revoke.
        service: Injected identity service dependency.
        auth: Authentication context with user info.

    Returns:
        IdentitySessionResponse with the revoked session details.

    Raises:
        403: User does not have access to this session's account.
        404: Session not found.
    """
    session = await service.get_session_or_raise(session_id)

    # Get identity to check account access
    identity = await service.get_by_id_or_raise(session.identity_id)

    # Check authorization
    if not auth.has_access_to_account(identity.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this session's account",
        )

    session = await service.revoke_session(session_id)
    return IdentitySessionResponse.from_domain(session)
