"""API-level routes (health checks, root endpoint, etc.)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from leadr.accounts.services.repositories import AccountRepository
from leadr.auth.api.schemas import CreateAPIKeyRequest, CreateAPIKeyResponse
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
