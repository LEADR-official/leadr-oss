"""API-level routes (health checks, root endpoint, etc.)."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from leadr.accounts.services.repositories import AccountRepository
from leadr.auth.api.schemas import (
    APIKeyResponse,
    CreateAPIKeyRequest,
    CreateAPIKeyResponse,
    UpdateAPIKeyRequest,
)
from leadr.auth.domain.api_key import APIKeyStatus
from leadr.auth.services.api_key_service import APIKeyService
from leadr.common.dependencies import DatabaseSession
from leadr.common.domain.models import EntityID

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    database: str


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(db: DatabaseSession) -> HealthResponse:
    """Health check endpoint.

    Verifies that the API is running and can connect to the database.
    """
    # Test database connectivity with a simple query
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        database=db_status,
    )


@router.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": "LEADR API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@router.post(
    "/api-keys",
    response_model=CreateAPIKeyResponse,
    status_code=201,
    tags=["API Keys"],
)
async def create_api_key(
    request: CreateAPIKeyRequest,
    db: DatabaseSession,
) -> CreateAPIKeyResponse:
    """Create a new API key for an account.

    The plain API key is returned only once in this response.
    Store it securely as it cannot be retrieved later.

    Returns:
        CreateAPIKeyResponse with the plain key included.

    Raises:
        404: Account not found.
    """
    # Verify account exists
    account_repo = AccountRepository(db)
    account_id = EntityID(value=request.account_id)
    account = await account_repo.get_by_id(account_id)

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Create API key
    service = APIKeyService(db)
    api_key, plain_key = await service.create_api_key(
        account_id=account_id,
        name=request.name,
        expires_at=request.expires_at,
    )

    # Return response with plain key
    return CreateAPIKeyResponse(
        id=api_key.id.value,
        name=api_key.name,
        key=plain_key,
        prefix=api_key.key_prefix,
        status=api_key.status,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


@router.get(
    "/api-keys",
    response_model=list[APIKeyResponse],
    tags=["API Keys"],
)
async def list_api_keys(
    db: DatabaseSession,
    account_id: UUID | None = Query(None, description="Filter by account ID"),
    status: APIKeyStatus | None = Query(None, description="Filter by status"),
) -> list[APIKeyResponse]:
    """List API keys with optional filters.

    Query parameters can be combined to narrow results.

    Args:
        account_id: Optional account ID to filter results.
        status: Optional status to filter results (active or revoked).

    Returns:
        List of API keys matching the filters.
    """
    service = APIKeyService(db)

    # Convert UUID to EntityID if provided
    entity_id = EntityID(value=account_id) if account_id else None

    # Get filtered list from service
    api_keys = await service.list_api_keys(
        account_id=entity_id,
        status=status.value if status else None,
    )

    # Convert to response models
    return [
        APIKeyResponse(
            id=key.id.value,
            account_id=key.account_id.value,
            name=key.name,
            prefix=key.key_prefix,
            status=key.status,
            last_used_at=key.last_used_at,
            expires_at=key.expires_at,
            created_at=key.created_at,
            updated_at=key.updated_at,
        )
        for key in api_keys
    ]


@router.get(
    "/api-keys/{key_id}",
    response_model=APIKeyResponse,
    tags=["API Keys"],
)
async def get_api_key(
    key_id: UUID,
    db: DatabaseSession,
) -> APIKeyResponse:
    """Get a single API key by ID.

    Args:
        key_id: The UUID of the API key to retrieve.

    Returns:
        APIKeyResponse with key details (excludes the plain key).

    Raises:
        404: API key not found.
    """
    service = APIKeyService(db)
    entity_id = EntityID(value=key_id)

    api_key = await service.get_api_key(entity_id)

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    return APIKeyResponse(
        id=api_key.id.value,
        account_id=api_key.account_id.value,
        name=api_key.name,
        prefix=api_key.key_prefix,
        status=api_key.status,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
        updated_at=api_key.updated_at,
    )


@router.patch(
    "/api-keys/{key_id}",
    response_model=APIKeyResponse,
    tags=["API Keys"],
)
async def update_api_key(
    key_id: UUID,
    request: UpdateAPIKeyRequest,
    db: DatabaseSession,
) -> APIKeyResponse:
    """Update an API key.

    Currently supports:
    - Updating status (e.g., to revoke a key)
    - Soft delete flag (placeholder for future implementation)

    Args:
        key_id: The UUID of the API key to update.
        request: Update request with optional status and deleted fields.

    Returns:
        APIKeyResponse with updated key details.

    Raises:
        404: API key not found.
    """
    service = APIKeyService(db)
    entity_id = EntityID(value=key_id)

    # Get existing key
    api_key = await service.get_api_key(entity_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    # Update status if provided
    if request.status is not None:
        api_key = await service.update_api_key_status(entity_id, request.status.value)

    # Handle soft delete if provided (placeholder for now)
    if request.deleted is not None and request.deleted:
        # TODO: Implement soft delete logic
        pass

    # Fetch updated key to return
    api_key = await service.get_api_key(entity_id)
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    return APIKeyResponse(
        id=api_key.id.value,
        account_id=api_key.account_id.value,
        name=api_key.name,
        prefix=api_key.key_prefix,
        status=api_key.status,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
        updated_at=api_key.updated_at,
    )
