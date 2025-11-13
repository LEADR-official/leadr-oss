"""API routes for device session management."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from leadr.auth.api.device_session_schemas import (
    DeviceSessionResponse,
    DeviceSessionUpdateRequest,
)
from leadr.auth.dependencies import AuthContextDep, QueryAccountIDDep
from leadr.auth.services.dependencies import DeviceServiceDep

router = APIRouter()


@router.get("/device-sessions", response_model=list[DeviceSessionResponse])
async def list_sessions(
    account_id: QueryAccountIDDep,
    service: DeviceServiceDep,
    device_id: UUID | None = None,
) -> list[DeviceSessionResponse]:
    """List device sessions for an account with optional filters.

    Returns all non-deleted device sessions for the specified account, with optional
    filtering by device.

    For regular users, account_id is automatically derived from their API key.
    For superadmins, account_id must be explicitly provided as a query parameter.

    Args:
        account_id: Account ID (auto-resolved for regular users, required for superadmins).
        service: Injected device service dependency.
        device_id: Optional device ID to filter by.

    Returns:
        List of DeviceSessionResponse objects matching the filter criteria.

    Raises:
        400: Superadmin did not provide account_id.
        403: User does not have access to the specified account.
    """
    sessions = await service.list_sessions(
        account_id=account_id,
        device_id=device_id,
    )

    return [DeviceSessionResponse.from_domain(session) for session in sessions]


@router.get("/device-sessions/{session_id}", response_model=DeviceSessionResponse)
async def get_session(
    session_id: UUID,
    service: DeviceServiceDep,
    auth: AuthContextDep,
) -> DeviceSessionResponse:
    """Get a device session by ID.

    Args:
        session_id: UUID of the session to retrieve.
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
    session_id: UUID,
    request: DeviceSessionUpdateRequest,
    service: DeviceServiceDep,
    auth: AuthContextDep,
) -> DeviceSessionResponse:
    """Update a device session (revoke).

    Allows revoking a device session to invalidate authentication.

    Args:
        session_id: UUID of the session to update.
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
