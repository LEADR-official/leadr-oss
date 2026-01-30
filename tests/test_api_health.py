"""Unit tests for API health check endpoint."""

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.common.dependencies import get_db


@pytest.mark.asyncio
async def test_liveness_check_returns_ok(mock_client_no_db: AsyncClient):
    """Test liveness probe returns ok without database check."""
    response = await mock_client_no_db.get("/health/live")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_health_check_does_not_require_authentication(
    test_app, mock_client_no_db: AsyncClient
):
    """Test that health check endpoint is public and does not require API key."""
    # Mock database session for health check
    mock_db = AsyncMock(spec=AsyncSession)
    mock_result = AsyncMock()
    mock_result.scalar = lambda: 1  # Non-async method
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def mock_get_db():
        yield mock_db

    test_app.dependency_overrides[get_db] = mock_get_db

    # Make request without any authentication headers
    response = await mock_client_no_db.get("/health")

    # Should succeed without authentication
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_root_endpoint_does_not_require_authentication(mock_client_no_db: AsyncClient):
    """Test that root endpoint is public and does not require API key."""
    # Make request without any authentication headers
    response = await mock_client_no_db.get("/")

    # Should succeed without authentication
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


@pytest.mark.asyncio
async def test_health_check_endpoint(test_app, mock_client_no_db: AsyncClient):
    """Test health check endpoint returns healthy status with database connection."""
    # Mock database session for health check
    mock_db = AsyncMock(spec=AsyncSession)
    mock_result = AsyncMock()
    mock_result.scalar = lambda: 1  # Non-async method
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def mock_get_db():
        yield mock_db

    test_app.dependency_overrides[get_db] = mock_get_db

    response = await mock_client_no_db.get("/health")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "healthy"


@pytest.mark.asyncio
async def test_root_endpoint(mock_client_no_db: AsyncClient):
    """Test root endpoint returns API information."""
    response = await mock_client_no_db.get("/")

    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "LEADR API"
    assert data["version"] == "0.1.0"
    assert data["docs"] == "/docs"
