"""Authentication dependencies for FastAPI."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException

from leadr.auth.domain.api_key import APIKey
from leadr.auth.domain.device import Device
from leadr.auth.services.dependencies import (
    APIKeyServiceDep,
    DeviceServiceDep,
    NonceServiceDep,
)


async def require_api_key(
    service: APIKeyServiceDep,
    api_key: Annotated[str | None, Header(alias="leadr-api-key")] = None,
) -> APIKey:
    """Require and validate API key authentication.

    This dependency validates the API key from the 'leadr-api-key' header
    and returns the authenticated APIKey entity. It also records usage
    of the key by updating the last_used_at timestamp.

    Args:
        api_key: The API key from the 'leadr-api-key' header.
        service: APIKeyService dependency.

    Returns:
        The authenticated APIKey entity.

    Raises:
        HTTPException: 401 Unauthorized if the API key is missing or invalid.

    Example:
        >>> @router.get("/protected")
        >>> async def protected_endpoint(
        >>>     authenticated_key: Annotated[APIKey, Depends(require_api_key)]
        >>> ):
        >>>     return {"account_id": authenticated_key.account_id}
    """
    if api_key is None:
        raise HTTPException(
            status_code=401,
            detail="API key required",
        )

    validated_key = await service.validate_api_key(api_key)

    if validated_key is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired API key",
        )

    return validated_key


async def require_device_token(
    service: DeviceServiceDep,
    authorization: Annotated[str | None, Header()] = None,
) -> Device:
    """Require and validate device token authentication.

    This dependency validates the device token from the 'Authorization' header
    (Bearer token format) and returns the authenticated Device entity.

    Args:
        authorization: The Authorization header value (e.g., "Bearer <token>").
        service: DeviceService dependency.

    Returns:
        The authenticated Device entity.

    Raises:
        HTTPException: 401 Unauthorized if the token is missing, malformed, or invalid.

    Example:
        >>> @router.get("/protected")
        >>> async def protected_endpoint(
        >>>     device: Annotated[Device, Depends(require_device_token)]
        >>> ):
        >>>     return {"game_id": device.game_id, "device_id": device.device_id}
    """
    if authorization is None:
        raise HTTPException(
            status_code=401,
            detail="Authorization token required",
        )

    # Parse Bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization format. Expected 'Bearer <token>'",
        )

    token = parts[1]

    # Validate device token
    validated_device = await service.validate_device_token(token)

    if validated_device is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired device token",
        )

    return validated_device


async def require_nonce(
    device: Device,
    service: NonceServiceDep,
    leadr_client_nonce: Annotated[str | None, Header(alias="leadr-client-nonce")] = None,
) -> bool:
    """Require and validate nonce for replay protection.

    This dependency validates the nonce from the 'leadr-client-nonce' header
    and consumes it (marks as used). Each nonce can only be used once.

    Args:
        device: The authenticated device entity.
        service: NonceService dependency.
        leadr_client_nonce: The nonce value from the 'leadr-client-nonce' header.

    Returns:
        True if nonce is valid and was successfully consumed.

    Raises:
        HTTPException: 412 Precondition Failed if nonce is missing, invalid,
            expired, already used, or belongs to a different device.

    Example:
        >>> @router.post("/protected")
        >>> async def protected_endpoint(
        >>>     device: DeviceTokenDep,
        >>>     nonce_valid: Annotated[bool, Depends(require_nonce)]
        >>> ):
        >>>     return {"status": "success"}
    """
    if leadr_client_nonce is None:
        raise HTTPException(
            status_code=412,
            detail="Nonce required",
        )

    try:
        await service.validate_and_consume_nonce(
            nonce_value=leadr_client_nonce,
            device_id=device.id,
        )
        return True
    except ValueError as e:
        error_msg = str(e).lower()

        if "not found" in error_msg:
            detail = "Invalid nonce"
        elif "does not belong" in error_msg:
            detail = "Nonce does not belong to this device"
        elif "already used" in error_msg:
            detail = "Nonce already used"
        elif "expired" in error_msg:
            detail = "Nonce expired"
        else:
            detail = "Invalid nonce"

        raise HTTPException(
            status_code=412,
            detail=detail,
        ) from None


# Type aliases for dependency injection
DeviceTokenDep = Annotated[Device, Depends(require_device_token)]
