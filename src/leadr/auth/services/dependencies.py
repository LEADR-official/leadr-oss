"""API Key service dependency injection factory."""

from typing import Annotated

from fastapi import Depends

from leadr.auth.services.api_key_service import APIKeyService
from leadr.common.dependencies import DatabaseSession


async def get_api_key_service(db: DatabaseSession) -> APIKeyService:
    """Get APIKeyService dependency.

    Args:
        db: Database session injected via dependency injection

    Returns:
        APIKeyService instance configured with the database session
    """
    return APIKeyService(db)


# Type alias for dependency injection in routes
APIKeyServiceDep = Annotated[APIKeyService, Depends(get_api_key_service)]
