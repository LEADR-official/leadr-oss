"""API routes for client authentication using Identity."""

from fastapi import APIRouter, HTTPException, Request, status

from leadr.auth.api.client_schemas import (
    NonceResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    StartSessionRequest,
    StartSessionResponse,
)
from leadr.auth.dependencies import ClientAuthContextDep
from leadr.auth.domain.identity import IdentityKind
from leadr.auth.services.dependencies import DeviceServiceDep, IdentityServiceDep, NonceServiceDep
from leadr.common.domain.exceptions import EntityNotFoundError

public_router = APIRouter(prefix="/client")
protected_router = APIRouter()


def _get_client_ip(request: Request) -> str | None:
    """Extract client IP from request headers."""
    # Check common headers for real IP when behind proxy
    for header in ["x-real-ip", "x-forwarded-for", "cf-connecting-ip"]:
        if value := request.headers.get(header):
            # x-forwarded-for can be comma-separated, take first
            return value.split(",")[0].strip()
    # Fall back to direct client
    if request.client:
        return request.client.host
    return None


@public_router.post(
    "/sessions",
    response_model=StartSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_session(
    request: Request,
    session_request: StartSessionRequest,
    device_service: DeviceServiceDep,
    identity_service: IdentityServiceDep,
) -> StartSessionResponse:
    """Start a new identity session for a game client.

    This endpoint authenticates game clients and provides JWT access tokens.
    It is idempotent - calling multiple times for the same fingerprint updates
    the device record and creates a new identity session.

    No authentication is required to call this endpoint (it IS the authentication).

    Args:
        request: FastAPI request object
        session_request: Session start request with game_id and fingerprint
        device_service: DeviceService dependency (for device lookup)
        identity_service: IdentityService dependency (for session creation)

    Returns:
        StartSessionResponse with identity info and access tokens

    Raises:
        404: Game not found
        422: Invalid request (missing required fields, invalid UUID format)
    """
    try:
        # 1. Get or create device (internal lookup only)
        device = await device_service.get_or_create_device(
            game_id=session_request.game_id,
            client_fingerprint=session_request.client_fingerprint,
            platform=session_request.platform,
            metadata=session_request.metadata,
        )

        # 2. Get or create identity from device
        identity, _ = await identity_service.get_or_create_identity(
            account_id=device.account_id,
            game_id=device.game_id,
            kind=IdentityKind.DEVICE,
            external_key=device.client_fingerprint,
        )

        # 3. Start identity session (creates tokens with identity_id)
        access_token, refresh_token, expires_in = await identity_service.start_session(
            identity=identity,
            ip_address=_get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            test_mode=session_request.test_mode,
        )
    except EntityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from None

    return StartSessionResponse.from_domain(
        identity, access_token, refresh_token, expires_in, test_mode=session_request.test_mode
    )


@public_router.post(
    "/sessions/refresh",
    response_model=RefreshTokenResponse,
    status_code=status.HTTP_200_OK,
)
async def refresh_session(
    request: RefreshTokenRequest,
    identity_service: IdentityServiceDep,
) -> RefreshTokenResponse:
    """Refresh an expired access token using a valid refresh token.

    This endpoint implements token rotation for security:
    - Returns new access and refresh tokens
    - Increments the token version
    - Invalidates the old refresh token (prevents replay attacks)

    No authentication is required (the refresh token itself is the credential).

    Args:
        request: Refresh token request
        identity_service: IdentityService dependency

    Returns:
        RefreshTokenResponse with new tokens

    Raises:
        401: Invalid or expired refresh token
        422: Invalid request (missing refresh_token)
    """
    result = await identity_service.refresh_access_token(request.refresh_token)

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


@protected_router.get(
    "/nonce",
    response_model=NonceResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_nonce(
    auth: ClientAuthContextDep,
    service: NonceServiceDep,
) -> NonceResponse:
    """Generate a fresh nonce for replay protection.

    Nonces are single-use tokens with short TTL (60 seconds) that clients must
    obtain before making mutating requests (POST, PATCH, DELETE). This prevents
    replay attacks by ensuring each request is fresh and authorized.

    Requires identity authentication via access token.

    Args:
        auth: Authenticated client auth context (identity guaranteed non-None)
        service: NonceService dependency

    Returns:
        NonceResponse with nonce_value and expires_at

    Raises:
        401: Invalid or missing access token

    Example:
        1. Client calls GET /client/nonce with Authorization header
        2. Server returns nonce_value and expires_at
        3. Client includes nonce in leadr-client-nonce header for mutations
        4. Server validates and consumes nonce (single-use)
    """
    # Access identity from auth context (guaranteed non-None by ClientAuthContext)
    nonce_value, expires_at = await service.generate_nonce(identity_id=auth.identity.id)

    return NonceResponse(
        nonce_value=nonce_value,
        expires_at=expires_at,
    )
