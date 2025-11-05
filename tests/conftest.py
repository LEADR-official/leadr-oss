"""Test configuration and fixtures."""

import sys
from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from leadr.common.database import get_db
from leadr.common.orm import Base
from leadr.config import settings


@pytest.fixture(scope="session", autouse=True)
def ensure_test_environment():
    """
    SAFETY CHECK: Ensure we're running in TEST environment.

    This prevents accidentally running tests against dev/prod databases
    and losing data when tests drop/recreate databases.
    """
    if settings.ENV != "TEST":
        print("\n🚨 DANGER: Tests must run in TEST environment!")
        print(f"Current ENV: {settings.ENV}")
        print("Expected: TEST")
        print("\nTo fix: Set ENV=TEST in your environment or use .env.test file")
        print("This safety check prevents accidentally deleting your dev database!\n")
        sys.exit(1)


@pytest.fixture(scope="session")
def test_database_name():
    """Generate unique test database name for the session."""
    return f"leadr_test_{str(uuid4())[:8]}"


@pytest.fixture(scope="session", autouse=True)
def setup_test_database(test_database_name: str):
    """Create and destroy test database for the session (sync fixture)."""
    # Use sync psycopg for database creation/destruction to avoid event loop issues
    from sqlalchemy import create_engine

    admin_url = f"postgresql+psycopg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/postgres"
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

    # Create test database
    with admin_engine.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{test_database_name}"'))
        conn.execute(text(f'CREATE DATABASE "{test_database_name}"'))

    admin_engine.dispose()

    yield

    # Clean up: drop test database
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        # Terminate active connections
        conn.execute(
            text(f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{test_database_name}' AND pid <> pg_backend_pid()
        """)
        )
        conn.execute(text(f'DROP DATABASE IF EXISTS "{test_database_name}"'))
    admin_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_engine(test_database_name: str) -> AsyncGenerator[AsyncEngine, None]:
    """Create async engine for the test database (function-scoped to avoid event loop issues)."""
    test_database_url = f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{test_database_name}"

    engine = create_async_engine(
        test_database_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=settings.DB_ECHO,
    )

    # Create all tables (idempotent - won't fail if tables exist)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Truncate all tables after test for isolation (faster than drop/create)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_maker() as cleanup_session:
        for table in reversed(Base.metadata.sorted_tables):
            await cleanup_session.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))
        await cleanup_session.commit()

    # Dispose engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create an async database session for each test.

    Table truncation is handled by the test_engine fixture cleanup.
    """
    # Create session factory
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with database session override."""
    from api.main import app

    # Override the get_db dependency to use our test session
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=f"http://testserver{settings.API_PREFIX}",
    ) as client:
        yield client

    # Clean up overrides
    app.dependency_overrides.clear()
