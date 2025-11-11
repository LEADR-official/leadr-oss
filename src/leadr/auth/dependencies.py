"""Authentication dependencies for FastAPI."""

from typing import Annotated

from fastapi import Header, HTTPException

from leadr.auth.domain.api_key import APIKey
from leadr.auth.domain.device import Device
from leadr.auth.services.dependencies import APIKeyServiceDep, DeviceServiceDep


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
