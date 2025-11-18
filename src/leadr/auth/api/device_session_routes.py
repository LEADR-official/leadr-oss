"""API routes for device session management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from leadr.auth.api.device_session_schemas import (
    DeviceSessionResponse,
    DeviceSessionUpdateRequest,
)
from leadr.auth.dependencies import AuthContextDep, QueryAccountIDDep
from leadr.auth.services.dependencies import DeviceServiceDep
from leadr.common.api.pagination import PaginatedResponse, PaginationMeta, PaginationParams
from leadr.common.domain.cursor import Cursor, CursorValidationError
from leadr.common.domain.ids import DeviceID, DeviceSessionID
from leadr.common.domain.pagination import PaginationDirection

router = APIRouter()


@router.get("/device-sessions", response_model=PaginatedResponse[DeviceSessionResponse])
async def list_sessions(
    account_id: QueryAccountIDDep,
    service: DeviceServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    device_id: Annotated[DeviceID | None, Query(description="Filter by device ID")] = None,
) -> PaginatedResponse[DeviceSessionResponse]:
    """List device sessions for an account with optional filters and pagination.

    Returns all non-deleted device sessions for the specified account, with optional
    filtering by device.

    For regular users, account_id is automatically derived from their API key.
    For superadmins, account_id must be explicitly provided as a query parameter.

    Pagination:
    - Default: 20 items per page, sorted by created_at:desc,id:asc
    - Custom sort: Use ?sort=created_at:asc,id:desc
    - Valid sort fields: id, created_at, updated_at
    - Navigation: Use next_cursor/prev_cursor from response

    Example:
        GET /v1/device-sessions?account_id=acc_123&device_id=dev_456&limit=50

    Args:
        account_id: Account ID (auto-resolved for regular users, required for superadmins).
        service: Injected device service dependency.
        pagination: Pagination parameters (cursor, limit, sort).
        device_id: Optional device ID to filter by.

    Returns:
        PaginatedResponse with device sessions and pagination metadata.

    Raises:
        400: Invalid cursor, sort field, or cursor state mismatch.
        400: Superadmin did not provide account_id.
        403: User does not have access to the specified account.
    """
    try:
        result = await service.list_sessions(
            account_id=account_id,
            device_id=device_id,
            pagination=pagination,
        )
    except (CursorValidationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Build filter dict for cursors
    filters_dict = {}
    if device_id is not None:
        filters_dict["device_id"] = str(device_id)

    # Build cursors from result positions
    next_cursor_str = None
    prev_cursor_str = None

    if result.next_position is not None:
        next_cursor = Cursor(
            position=result.next_position,
            sort_fields=pagination.sort_spec,
            filters=filters_dict,
            direction=PaginationDirection.FORWARD,
        )
        next_cursor_str = next_cursor.encode()

    if result.prev_position is not None:
        prev_cursor = Cursor(
            position=result.prev_position,
            sort_fields=pagination.sort_spec,
            filters=filters_dict,
            direction=PaginationDirection.BACKWARD,
        )
        prev_cursor_str = prev_cursor.encode()

    # Convert domain entities to response models
    response_items = [DeviceSessionResponse.from_domain(session) for session in result.items]

    # Build paginated response
    return PaginatedResponse(
        data=response_items,
        pagination=PaginationMeta(
            next_cursor=next_cursor_str,
            prev_cursor=prev_cursor_str,
            has_next=result.has_next,
            has_prev=result.has_prev,
            count=result.count,
        ),
    )


@router.get("/device-sessions/{session_id}", response_model=DeviceSessionResponse)
async def get_session(
    session_id: DeviceSessionID,
    service: DeviceServiceDep,
    auth: AuthContextDep,
) -> DeviceSessionResponse:
    """Get a device session by ID.

    Args:
        session_id: Session identifier to retrieve.
        service: Injected device service dependency.
        auth: Authentication context with user info.

    Returns:
        DeviceSessionResponse with the session details.

    Raises:
        403: User does not have access to this session's account.
        404: Session not found or soft-deleted.
    """
    session = await service.get_session_or_raise(session_id)

    # Get the device to check account access
    device = await service.get_by_id_or_raise(session.device_id)

    # Check authorization
    if not auth.has_access_to_account(device.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this session's account",
        )

    return DeviceSessionResponse.from_domain(session)


@router.patch("/device-sessions/{session_id}", response_model=DeviceSessionResponse)
async def update_session(
    session_id: DeviceSessionID,
    request: DeviceSessionUpdateRequest,
    service: DeviceServiceDep,
    auth: AuthContextDep,
) -> DeviceSessionResponse:
    """Update a device session (revoke).

    Allows revoking a device session to invalidate authentication.

    Args:
        session_id: Session identifier to update.
        request: Update details (revoked status).
        service: Injected device service dependency.
        auth: Authentication context with user info.

    Returns:
        DeviceSessionResponse with the updated session details.

    Raises:
        403: User does not have access to this session's account.
        404: Session not found.
        400: Invalid request or no revoked field provided.
    """
    # Get the session to check account access
    session = await service.get_session_or_raise(session_id)

    # Get the device to check account access
    device = await service.get_by_id_or_raise(session.device_id)

    # Check authorization
    if not auth.has_access_to_account(device.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this session's account",
        )

    # Handle revoke update
    if request.revoked is True:
        session = await service.revoke_session(session_id)
    else:
        raise HTTPException(
            status_code=400,
            detail="Must provide revoked field set to true",
        )

    return DeviceSessionResponse.from_domain(session)
