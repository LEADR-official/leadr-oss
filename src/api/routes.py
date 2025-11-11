"""API-level routes (health checks, root endpoint, etc.)."""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import text

from leadr.common.dependencies import DatabaseSession

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(description="Overall API health status (healthy, degraded, or unhealthy)")
    database: str = Field(description="Database connection status")


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(db: DatabaseSession) -> HealthResponse:
    """Health check endpoint.

    Verifies that the API is running and can connect to the database.
    Returns degraded status if database connectivity fails.

    Args:
        db: Database session dependency.

    Returns:
        HealthResponse with API and database status.
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
    """Root endpoint.

    Returns basic API information including version and documentation URL.

    Returns:
        Dict containing API metadata.
    """
    return {
        "message": "LEADR API",
        "version": "0.1.0",
        "docs": "/docs",
    }
