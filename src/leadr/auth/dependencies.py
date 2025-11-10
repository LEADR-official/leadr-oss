"""Authentication dependencies for FastAPI."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.auth.domain.api_key import APIKey
from leadr.auth.services.api_key_service import APIKeyService
from leadr.common.dependencies import DatabaseSession


async def require_api_key(
    api_key: Annotated[str | None, Header(alias="leadr-api-key")] = None,
    db: DatabaseSession = None,
) -> APIKey:
    """Require and validate API key authentication.

    This dependency validates the API key from the 'leadr-api-key' header
    and returns the authenticated APIKey entity. It also records usage
    of the key by updating the last_used_at timestamp.

    Args:
        api_key: The API key from the 'leadr-api-key' header.
        db: Database session dependency.

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

    service = APIKeyService(db)
    validated_key = await service.validate_api_key(api_key)

    if validated_key is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired API key",
        )

    return validated_key
