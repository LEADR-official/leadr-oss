"""API routes for client device authentication."""

from fastapi import APIRouter, HTTPException, status

from leadr.auth.api.schemas import (
    RefreshTokenRequest,
    RefreshTokenResponse,
    StartSessionRequest,
    StartSessionResponse,
)
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
        device, access_token, refresh_token, expires_in = await service.start_session(
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

    return StartSessionResponse.from_domain(device, access_token, refresh_token, expires_in)


@router.post(
    "/client/sessions/refresh",
    response_model=RefreshTokenResponse,
    status_code=status.HTTP_200_OK,
)
async def refresh_session(
    request: RefreshTokenRequest,
    service: DeviceServiceDep,
) -> RefreshTokenResponse:
    """Refresh an expired access token using a valid refresh token.

    This endpoint implements token rotation for security:
    - Returns new access and refresh tokens
    - Increments the token version
    - Invalidates the old refresh token (prevents replay attacks)

    No authentication is required (the refresh token itself is the credential).

    Args:
        request: Refresh token request
        service: DeviceService dependency

    Returns:
        RefreshTokenResponse with new tokens

    Raises:
        401: Invalid or expired refresh token
        422: Invalid request (missing refresh_token)
    """
    result = await service.refresh_access_token(request.refresh_token)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    access_token, refresh_token, expires_in = result

    return RefreshTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )
