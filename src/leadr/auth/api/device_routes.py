"""API routes for device management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from leadr.auth.api.device_schemas import DeviceResponse, DeviceUpdateRequest
from leadr.auth.dependencies import AdminAuthContextDep
from leadr.auth.domain.device import DeviceStatus
from leadr.auth.services.dependencies import DeviceServiceDep
from leadr.common.api.pagination import PaginatedResponse, PaginationParams
from leadr.common.domain.cursor import CursorValidationError
from leadr.common.domain.ids import AccountID, DeviceID, GameID

router = APIRouter()


@router.get("/devices", response_model=PaginatedResponse[DeviceResponse])
async def list_devices(
    auth: AdminAuthContextDep,
    service: DeviceServiceDep,
    pagination: Annotated[PaginationParams, Depends()],
    account_id: Annotated[AccountID | None, Query(description="Account ID filter")] = None,
    game_id: Annotated[GameID | None, Query(description="Filter by game ID")] = None,
    device_status: Annotated[
        str | None, Query(alias="status", description="Filter by status")
    ] = None,
) -> PaginatedResponse[DeviceResponse]:
    """List devices for an account with optional filters and pagination.

    Returns all non-deleted devices for the specified account, with optional
    filtering by game or status.

    For regular users, account_id is automatically derived from their API key.
    For superadmins, account_id is optional - if omitted, returns devices from all accounts.

    Pagination:
    - Default: 20 items per page, sorted by created_at:desc,id:asc
    - Custom sort: Use ?sort=name:asc,created_at:desc
    - Valid sort fields: id, platform, created_at, updated_at
    - Navigation: Use next_cursor/prev_cursor from response

    Example:
        GET /v1/devices?account_id=acc_123&game_id=game_456&status=active&limit=50

    Args:
        auth: Authentication context with user info.
        service: Injected device service dependency.
        pagination: Pagination parameters (cursor, limit, sort).
        account_id: Optional account_id query parameter (superadmins can omit to see all).
        game_id: Optional game ID to filter by.
        device_status: Optional status to filter by (active, banned, suspended).

    Returns:
        PaginatedResponse with devices and pagination metadata.

    Raises:
        400: Invalid cursor, sort field, or cursor state mismatch.
        403: User does not have access to the specified account.
    """
    # Superadmin without account_id = None (all accounts)
    # Superadmin with account_id = that specific account
    # Regular user = always their account_id (ignores query param)
    effective_account_id = account_id if auth.is_superadmin else auth.account_id
    try:
        result = await service.list_devices(
            account_id=effective_account_id,
            game_id=game_id,
            status=device_status,
            pagination=pagination,
        )
    except (CursorValidationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Build filter dict for cursors
    filters_dict = {}
    if game_id is not None:
        filters_dict["game_id"] = str(game_id)
    if device_status is not None:
        filters_dict["status"] = device_status

    return PaginatedResponse.from_paginated_result(
        result=result,
        pagination=pagination,
        filters=filters_dict,
        response_model=DeviceResponse,
    )


@router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: DeviceID,
    service: DeviceServiceDep,
    auth: AdminAuthContextDep,
) -> DeviceResponse:
    """Get a device by ID.

    Args:
        device_id: Device identifier to retrieve.
        service: Injected device service dependency.
        auth: Authentication context with user info.

    Returns:
        DeviceResponse with the device details.

    Raises:
        403: User does not have access to this device's account.
        404: Device not found or soft-deleted.
    """
    device = await service.get_by_id_or_raise(device_id)

    # Check authorization
    if not auth.has_access_to_account(device.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this device's account",
        )

    return DeviceResponse.from_domain(device)


@router.patch("/devices/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: DeviceID,
    request: DeviceUpdateRequest,
    service: DeviceServiceDep,
    auth: AdminAuthContextDep,
) -> DeviceResponse:
    """Update a device (change status).

    Allows changing device status to ban, suspend, or activate devices.

    Args:
        device_id: Device identifier to update.
        request: Update details (status).
        service: Injected device service dependency.
        auth: Authentication context with user info.

    Returns:
        DeviceResponse with the updated device details.

    Raises:
        403: User does not have access to this device's account.
        404: Device not found.
        400: Invalid status value.
    """
    # Get the device to check account access
    device = await service.get_by_id_or_raise(device_id)

    # Check authorization
    if not auth.has_access_to_account(device.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this device's account",
        )

    # Handle status update
    if request.status is not None:
        try:
            status_enum = DeviceStatus(request.status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid status: {request.status}. Must be one of: active, banned, suspended"
                ),
            ) from None

        # Update device status based on enum
        if status_enum == DeviceStatus.BANNED:
            device = await service.ban_device(device_id)
        elif status_enum == DeviceStatus.SUSPENDED:
            device = await service.suspend_device(device_id)
        elif status_enum == DeviceStatus.ACTIVE:
            device = await service.activate_device(device_id)
    else:
        raise HTTPException(
            status_code=400,
            detail="Must provide status field",
        )

    return DeviceResponse.from_domain(device)
