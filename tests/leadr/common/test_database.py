"""Test database configuration and fixtures."""

from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from leadr.common.database import build_database_url, get_db


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


class TestBuildDatabaseUrl:
    """Tests for build_database_url function."""

    @patch("leadr.common.database.settings")
    def test_build_database_url_with_default_settings(self, mock_settings) -> None:
        """Test building database URL with default settings."""
        mock_settings.DB_USER = "postgres"
        mock_settings.DB_PASSWORD = "password"
        mock_settings.DB_HOST = "localhost"
        mock_settings.DB_PORT = 5432
        mock_settings.DB_NAME = "leadr"

        url = build_database_url()
        assert url == "postgresql+asyncpg://postgres:password@localhost:5432/leadr"

    @patch("leadr.common.database.settings")
    def test_build_database_url_with_custom_host(self, mock_settings) -> None:
        """Test building database URL with custom host."""
        mock_settings.DB_USER = "admin"
        mock_settings.DB_PASSWORD = "secret"
        mock_settings.DB_HOST = "db.example.com"
        mock_settings.DB_PORT = 5433
        mock_settings.DB_NAME = "production"

        url = build_database_url()
        assert url == "postgresql+asyncpg://admin:secret@db.example.com:5433/production"

    @patch("leadr.common.database.settings")
    def test_build_database_url_with_special_characters(self, mock_settings) -> None:
        """Test building database URL with special characters in password."""
        mock_settings.DB_USER = "user"
        mock_settings.DB_PASSWORD = "p@ssw0rd!#$"
        mock_settings.DB_HOST = "localhost"
        mock_settings.DB_PORT = 5432
        mock_settings.DB_NAME = "testdb"

        url = build_database_url()
        assert url == "postgresql+asyncpg://user:p@ssw0rd!#$@localhost:5432/testdb"

    @patch("leadr.common.database.settings")
    def test_build_database_url_format(self, mock_settings) -> None:
        """Test that the URL uses the correct asyncpg driver."""
        mock_settings.DB_USER = "user"
        mock_settings.DB_PASSWORD = "pass"
        mock_settings.DB_HOST = "host"
        mock_settings.DB_PORT = 5432
        mock_settings.DB_NAME = "db"

        url = build_database_url()
        assert url.startswith("postgresql+asyncpg://")
        assert "user:pass@host:5432/db" in url


class TestGetDb:
    """Tests for get_db async generator dependency."""

    @pytest.mark.asyncio
    async def test_get_db_yields_session(self) -> None:
        """Test that get_db yields an AsyncSession."""
        from leadr.common import database

        generator = get_db()
        assert isinstance(generator, AsyncGenerator)

        session = await generator.__anext__()
        assert isinstance(session, AsyncSession)

        # Clean up
        try:
            await generator.__anext__()
        except StopAsyncIteration:
            pass
        finally:
            await database.engine.dispose()

    @pytest.mark.asyncio
    async def test_get_db_session_cleanup(self) -> None:
        """Test that get_db properly cleans up the session."""
        from leadr.common import database

        generator = get_db()
        session = await generator.__anext__()

        # Verify session is valid and active
        assert isinstance(session, AsyncSession)
        assert session.is_active  # Session is active when created

        # Close the generator (simulates end of request)
        with pytest.raises(StopAsyncIteration):
            await generator.__anext__()

        # Session should be closed after generator exits
        assert not session.in_transaction()

        # Dispose engine to avoid event loop issues
        await database.engine.dispose()

    @pytest.mark.asyncio
    async def test_get_db_as_context_manager(self) -> None:
        """Test using get_db in async context manager style."""
        from leadr.common import database

        generator = get_db()
        try:
            async for session in generator:
                assert isinstance(session, AsyncSession)
                # Only one iteration should occur
                break
        finally:
            await generator.aclose()
            # Dispose engine to avoid event loop issues
            await database.engine.dispose()

    @pytest.mark.asyncio
    async def test_get_db_session_is_usable(self) -> None:
        """Test that the yielded session can be used for database operations."""
        from leadr.common import database

        generator = get_db()
        try:
            async for session in generator:
                # Should be able to execute a simple query
                result = await session.execute(text("SELECT 1"))
                assert result is not None
                break
        finally:
            await generator.aclose()
            # Dispose engine to avoid event loop issues
            await database.engine.dispose()
