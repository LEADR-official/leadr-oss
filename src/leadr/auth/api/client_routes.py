"""API routes for client device authentication."""

from fastapi import APIRouter, HTTPException, status

from leadr.auth.api.schemas import StartSessionRequest, StartSessionResponse
from leadr.auth.services.dependencies import DeviceServiceDep
from leadr.common.domain.exceptions import EntityNotFoundError

router = APIRouter()


@router.post(
    "/client/sessions",
    response_model=StartSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_session(
    request: StartSessionRequest,
    service: DeviceServiceDep,
) -> StartSessionResponse:
    """Start a new device session for a game client.

    This endpoint authenticates game clients and provides JWT access tokens.
    It is idempotent - calling multiple times for the same device updates last_seen_at
    and generates a new access token.

    No authentication is required to call this endpoint (it IS the authentication).

    Args:
        request: Session start request with game_id and device_id
        service: DeviceService dependency

    Returns:
        StartSessionResponse with device info and access token

    Raises:
        404: Game not found
        422: Invalid request (missing required fields, invalid UUID format)
    """
    try:
        device, access_token, expires_in = await service.start_session(
            game_id=request.game_id,
            device_id=request.device_id,
            platform=request.platform,
            metadata=request.metadata,
        )
    except EntityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from None

    return StartSessionResponse.from_domain(device, access_token, expires_in)
