"""API routes for device management."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from leadr.auth.api.device_schemas import DeviceResponse, DeviceUpdateRequest
from leadr.auth.dependencies import AuthContextDep, QueryAccountIDDep
from leadr.auth.domain.device import DeviceStatus
from leadr.auth.services.dependencies import DeviceServiceDep
from leadr.common.domain.ids import DeviceID, GameID

router = APIRouter()


@router.get("/devices", response_model=list[DeviceResponse])
async def list_devices(
    account_id: QueryAccountIDDep,
    service: DeviceServiceDep,
    game_id: UUID | None = None,
    status: str | None = None,
) -> list[DeviceResponse]:
    """List devices for an account with optional filters.

    Returns all non-deleted devices for the specified account, with optional
    filtering by game or status.

    For regular users, account_id is automatically derived from their API key.
    For superadmins, account_id must be explicitly provided as a query parameter.

    Args:
        account_id: Account ID (auto-resolved for regular users, required for superadmins).
        service: Injected device service dependency.
        game_id: Optional game ID to filter by.
        status: Optional status to filter by (active, banned, suspended).

    Returns:
        List of DeviceResponse objects matching the filter criteria.

    Raises:
        400: Superadmin did not provide account_id.
        403: User does not have access to the specified account.
    """
    devices = await service.list_devices(
        account_id=account_id,
        game_id=GameID(game_id) if game_id else None,
        status=status,
    )

    return [DeviceResponse.from_domain(device) for device in devices]


@router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: UUID,
    service: DeviceServiceDep,
    auth: AuthContextDep,
) -> DeviceResponse:
    """Get a device by ID.

    Args:
        device_id: UUID of the device to retrieve.
        service: Injected device service dependency.
        auth: Authentication context with user info.

    Returns:
        DeviceResponse with the device details.

    Raises:
        403: User does not have access to this device's account.
        404: Device not found or soft-deleted.
    """
    device = await service.get_by_id_or_raise(DeviceID(device_id))

    # Check authorization
    if not auth.has_access_to_account(device.account_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this device's account",
        )

    return DeviceResponse.from_domain(device)


@router.patch("/devices/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: UUID,
    request: DeviceUpdateRequest,
    service: DeviceServiceDep,
    auth: AuthContextDep,
) -> DeviceResponse:
    """Update a device (change status).

    Allows changing device status to ban, suspend, or activate devices.

    Args:
        device_id: UUID of the device to update.
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
    device_id_typed = DeviceID(device_id)

    # Get the device to check account access
    device = await service.get_by_id_or_raise(device_id_typed)

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
            device = await service.ban_device(device_id_typed)
        elif status_enum == DeviceStatus.SUSPENDED:
            device = await service.suspend_device(device_id_typed)
        elif status_enum == DeviceStatus.ACTIVE:
            device = await service.activate_device(device_id_typed)
    else:
        raise HTTPException(
            status_code=400,
            detail="Must provide status field",
        )

    return DeviceResponse.from_domain(device)
