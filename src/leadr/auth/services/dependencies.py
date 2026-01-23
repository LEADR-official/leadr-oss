"""Auth service dependency injection factories."""

from typing import Annotated

from fastapi import Depends

from leadr.auth.services.api_key_service import APIKeyService
from leadr.auth.services.device_service import DeviceService
from leadr.auth.services.identity_service import IdentityService
from leadr.auth.services.nonce_service import NonceService
from leadr.common.dependencies import DatabaseSession


async def get_api_key_service(db: DatabaseSession) -> APIKeyService:
    """Get APIKeyService dependency.

    Args:
        db: Database session injected via dependency injection

    Returns:
        APIKeyService instance configured with the database session
    """
    return APIKeyService(db)


async def get_device_service(db: DatabaseSession) -> DeviceService:
    """Get DeviceService dependency.

    Args:
        db: Database session injected via dependency injection

    Returns:
        DeviceService instance configured with the database session
    """
    return DeviceService(db)


async def get_nonce_service(db: DatabaseSession) -> NonceService:
    """Get NonceService dependency.

    Args:
        db: Database session injected via dependency injection

    Returns:
        NonceService instance configured with the database session
    """
    return NonceService(db)


async def get_identity_service(db: DatabaseSession) -> IdentityService:
    """Get IdentityService dependency.

    Args:
        db: Database session injected via dependency injection

    Returns:
        IdentityService instance configured with the database session
    """
    return IdentityService(db)


# Type aliases for dependency injection in routes
APIKeyServiceDep = Annotated[APIKeyService, Depends(get_api_key_service)]
DeviceServiceDep = Annotated[DeviceService, Depends(get_device_service)]
IdentityServiceDep = Annotated[IdentityService, Depends(get_identity_service)]
NonceServiceDep = Annotated[NonceService, Depends(get_nonce_service)]
