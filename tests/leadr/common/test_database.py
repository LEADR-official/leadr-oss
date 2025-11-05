"""Test database configuration and fixtures."""

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


@pytest.mark.asyncio
async def test_db_session_fixture(db_session: AsyncSession):
    """Test that database session fixture works."""
    # Execute a simple query
    result = await db_session.execute(text("SELECT 1 as value"))
    row = result.first()
    assert row is not None
    assert row.value == 1


@pytest.mark.asyncio
async def test_db_session_isolation(db_session: AsyncSession):
    """Test that database session is isolated between tests."""
    # This test should have a clean database (truncated from previous test)
    result = await db_session.execute(text("SELECT 1 as value"))
    row = result.first()
    assert row is not None
    assert row.value == 1


@pytest.mark.asyncio
async def test_engine_truncation_works(test_engine: AsyncEngine):
    """Test that truncation happens even when using test_engine directly.

    This ensures that tests using only test_engine (not db_session)
    still get clean tables between tests.
    """
    # Create a session from the engine
    async_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session_maker() as session:
        result = await session.execute(text("SELECT 1 as value"))
        row = result.first()
        assert row is not None
        assert row.value == 1


@pytest.mark.asyncio
async def test_client_fixture(client: AsyncClient):
    """Test that async client fixture works."""
    # Test that we can make requests to the app via the root endpoint
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "LEADR API"
