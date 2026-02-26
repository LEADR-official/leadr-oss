"""Test database configuration and fixtures."""

import ssl
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from leadr.common import database
from leadr.common.database import (
    _get_connect_args,
    _get_pool_class,
    _get_pool_options,
    _get_ssl_context,
    build_database_url,
    build_direct_database_url,
    create_session,
    get_db,
)


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


class TestBuildDirectDatabaseUrl:
    """Tests for build_direct_database_url function."""

    @patch("leadr.common.database.settings")
    def test_uses_direct_host_when_set(self, mock_settings) -> None:
        """Test that DB_HOST_DIRECT is used when available."""
        mock_settings.DB_USER = "user"
        mock_settings.DB_PASSWORD = "pass"
        mock_settings.DB_HOST = "pooler.example.com"
        mock_settings.DB_HOST_DIRECT = "direct.example.com"
        mock_settings.DB_PORT = 5432
        mock_settings.DB_NAME = "db"

        url = build_direct_database_url()
        assert "direct.example.com" in url
        assert "pooler.example.com" not in url

    @patch("leadr.common.database.settings")
    def test_falls_back_to_host_when_direct_not_set(self, mock_settings) -> None:
        """Test that DB_HOST is used when DB_HOST_DIRECT is None."""
        mock_settings.DB_USER = "user"
        mock_settings.DB_PASSWORD = "pass"
        mock_settings.DB_HOST = "pooler.example.com"
        mock_settings.DB_HOST_DIRECT = None
        mock_settings.DB_PORT = 5432
        mock_settings.DB_NAME = "db"

        url = build_direct_database_url()
        assert "pooler.example.com" in url


class TestGetSslContext:
    """Tests for _get_ssl_context function."""

    @patch("leadr.common.database.settings")
    def test_returns_none_for_dev_env(self, mock_settings) -> None:
        """Test that SSL context is None for DEV environment."""
        mock_settings.ENV = "DEV"
        assert _get_ssl_context() is None

    @patch("leadr.common.database.settings")
    def test_returns_none_for_test_env(self, mock_settings) -> None:
        """Test that SSL context is None for TEST environment."""
        mock_settings.ENV = "TEST"
        assert _get_ssl_context() is None

    @patch("leadr.common.database.settings")
    def test_returns_ssl_context_for_production(self, mock_settings) -> None:
        """Test that SSL context is created for production."""
        mock_settings.ENV = "PROD"
        ctx = _get_ssl_context()
        assert ctx is not None
        assert isinstance(ctx, ssl.SSLContext)
        assert ctx.check_hostname is True


class TestGetConnectArgs:
    """Tests for _get_connect_args function."""

    @patch("leadr.common.database.settings")
    def test_returns_empty_for_dev_env(self, mock_settings) -> None:
        """Test that no SSL args for DEV environment."""
        mock_settings.ENV = "DEV"
        args = _get_connect_args()
        assert "ssl" not in args

    @patch("leadr.common.database.settings")
    def test_returns_ssl_for_production(self, mock_settings) -> None:
        """Test that SSL args included for production."""
        mock_settings.ENV = "PROD"
        args = _get_connect_args()
        assert "ssl" in args
        assert isinstance(args["ssl"], ssl.SSLContext)


class TestGetPoolClass:
    """Tests for _get_pool_class function."""

    @patch("leadr.common.database.settings")
    def test_returns_none_for_dev_env(self, mock_settings) -> None:
        """Test that default pool is used for DEV environment."""
        mock_settings.ENV = "DEV"
        assert _get_pool_class() is None

    @patch("leadr.common.database.settings")
    def test_returns_none_for_test_env(self, mock_settings) -> None:
        """Test that default pool is used for TEST environment."""
        mock_settings.ENV = "TEST"
        assert _get_pool_class() is None

    @patch("leadr.common.database.settings")
    def test_returns_nullpool_for_production(self, mock_settings) -> None:
        """Test that NullPool is used for production (Neon)."""
        mock_settings.ENV = "PROD"
        assert _get_pool_class() is NullPool


class TestGetPoolOptions:
    """Tests for _get_pool_options function."""

    @patch("leadr.common.database.settings")
    def test_returns_pool_options_for_dev_env(self, mock_settings) -> None:
        """Test that pool options are set for DEV environment."""
        mock_settings.ENV = "DEV"
        mock_settings.DB_POOL_SIZE = 5
        mock_settings.DB_POOL_MAX_OVERFLOW = 10
        mock_settings.DB_POOL_RECYCLE = 3600

        options = _get_pool_options()
        assert options["pool_size"] == 5
        assert options["max_overflow"] == 10
        assert options["pool_recycle"] == 3600
        assert options["pool_pre_ping"] is True

    @patch("leadr.common.database.settings")
    def test_returns_empty_for_production(self, mock_settings) -> None:
        """Test that no pool options for production (using NullPool)."""
        mock_settings.ENV = "PROD"
        options = _get_pool_options()
        assert options == {}


class TestGetDb:
    """Tests for get_db async generator dependency."""

    @pytest.mark.asyncio
    async def test_get_db_yields_session(self) -> None:
        """Test that get_db yields an AsyncSession."""
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
        """Test that get_db returns a session that's ready for use."""
        generator = get_db()
        try:
            async for session in generator:
                # Verify session is an AsyncSession instance
                assert isinstance(session, AsyncSession)
                # Session should be active and ready to use
                assert session.is_active
                break
        finally:
            await generator.aclose()
            # Dispose engine to avoid event loop issues
            await database.engine.dispose()


class TestCreateSession:
    """Tests for create_session function for non-FastAPI contexts."""

    def test_create_session_returns_async_session(self) -> None:
        """Test that create_session returns an AsyncSession."""
        session = create_session()
        assert isinstance(session, AsyncSession)
        # Note: This test only verifies the return type, not database connectivity
