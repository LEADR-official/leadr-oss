"""Authentication dependencies for FastAPI."""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException

from leadr.accounts.domain.user import User
from leadr.accounts.services.dependencies import UserServiceDep
from leadr.auth.domain.api_key import APIKey
from leadr.auth.domain.device import Device
from leadr.auth.services.dependencies import (
    APIKeyServiceDep,
    DeviceServiceDep,
    NonceServiceDep,
)


@dataclass(frozen=True)
class AuthContext:
    """Authentication context providing API key and user information.

    This context is returned by the require_api_key dependency and provides
    both the authenticated API key and the associated user. It includes helper
    methods for authorization checks.

    Attributes:
        api_key: The authenticated API key entity.
        user: The user associated with the API key.
    """

    api_key: APIKey
    user: User

    @property
    def is_superadmin(self) -> bool:
        """Check if the authenticated user has superadmin privileges.

        Returns:
            True if user is a superadmin, False otherwise.
        """
        return self.user.super_admin

    def has_access_to_account(self, account_id: UUID) -> bool:
        """Check if the authenticated user has access to a specific account.

        Superadmins have access to all accounts. Regular users only have
        access to their own account.

        Args:
            account_id: The account ID to check access for.

        Returns:
            True if user has access to the account, False otherwise.
        """
        return self.is_superadmin or self.api_key.account_id == account_id


async def require_api_key(
    api_key_service: APIKeyServiceDep,
    user_service: UserServiceDep,
    api_key: Annotated[str | None, Header(alias="leadr-api-key")] = None,
) -> AuthContext:
    """Require and validate API key authentication.

    This dependency validates the API key from the 'leadr-api-key' header
    and returns an AuthContext containing both the authenticated API key
    and the associated user. It also records usage of the key by updating
    the last_used_at timestamp.

    Args:
        api_key: The API key from the 'leadr-api-key' header.
        api_key_service: APIKeyService dependency.
        user_service: UserService dependency.

    Returns:
        AuthContext containing the authenticated API key and user.

    Raises:
        HTTPException: 401 Unauthorized if the API key is missing, invalid,
            or if the associated user is not found.

    Example:
        >>> @router.get("/protected")
        >>> async def protected_endpoint(
        >>>     auth: AuthContextDep
        >>> ):
        >>>     return {"account_id": auth.api_key.account_id, "is_superadmin": auth.is_superadmin}
    """
    if api_key is None:
        raise HTTPException(
            status_code=401,
            detail="API key required",
        )

    validated_key = await api_key_service.validate_api_key(api_key)

    if validated_key is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired API key",
        )

    # Fetch the user associated with the API key
    user = await user_service.get_user(validated_key.user_id)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User associated with API key not found",
        )

    return AuthContext(api_key=validated_key, user=user)


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
AuthContextDep = Annotated[AuthContext, Depends(require_api_key)]
DeviceTokenDep = Annotated[Device, Depends(require_device_token)]
