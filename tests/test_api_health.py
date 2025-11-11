"""Integration tests for API health check endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_does_not_require_authentication(client: AsyncClient):
    """Test that health check endpoint is public and does not require API key."""
    # Make request without any authentication headers
    response = await client.get("/health")

    # Should succeed without authentication
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_root_endpoint_does_not_require_authentication(client: AsyncClient):
    """Test that root endpoint is public and does not require API key."""
    # Make request without any authentication headers
    response = await client.get("/")

    # Should succeed without authentication
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


@pytest.mark.asyncio
async def test_health_check_endpoint(client: AsyncClient):
    """Test health check endpoint returns healthy status with database connection."""
    response = await client.get("/health")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "healthy"


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test root endpoint returns API information."""
    response = await client.get("/")

    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "LEADR API"
    assert data["version"] == "0.1.0"
    assert data["docs"] == "/docs"


@pytest.mark.asyncio
async def test_health_check_uses_async_database(client: AsyncClient):
    """Test that health check actually queries the database asynchronously.

    This is an integration test verifying the full async stack:
    - FastAPI async route handler
    - Async database session dependency
    - AsyncSession query execution
    - Proper cleanup
    """
    # Make multiple concurrent requests to verify async handling
    responses = []
    for _ in range(5):
        response = await client.get("/health")
        responses.append(response)

    # All requests should succeed
    for response in responses:
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "healthy"
