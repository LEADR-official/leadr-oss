"""Test configuration and fixtures."""

import asyncio
import sys
from collections.abc import AsyncGenerator, Callable
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from leadr.common.database import get_db

# Import all ORM models to register them with metadata
from leadr.common.orm import Base
from leadr.config import settings


def override_dependency(
    client: TestClient, dependency: Callable[..., Any], override: Callable[..., Any]
) -> None:
    """Override a FastAPI dependency in a type-safe way.

    Args:
        client: The TestClient instance
        dependency: The dependency function to override
        override: The override function to use

    Raises:
        AssertionError: If the client doesn't wrap a FastAPI app
    """
    app = client.app
    assert isinstance(app, FastAPI), "TestClient must wrap a FastAPI app"
    app.dependency_overrides[dependency] = override


def clear_dependency_override(client: TestClient, dependency: Callable[..., Any]) -> None:
    """Clear a FastAPI dependency override in a type-safe way.

    Args:
        client: The TestClient instance
        dependency: The dependency function to clear

    Raises:
        AssertionError: If the client doesn't wrap a FastAPI app
    """
    app = client.app
    assert isinstance(app, FastAPI), "TestClient must wrap a FastAPI app"
    if dependency in app.dependency_overrides:
        del app.dependency_overrides[dependency]


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
def test_database():
    """Create and destroy test database for the session."""
    # Force dedicated test database name - NEVER use settings.DB_NAME directly
    test_db_name = f"leadr-test-{str(uuid4())[:4]}"

    # Connect to postgres server without specifying database
    admin_url = f"postgresql+psycopg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/postgres"
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

    # Create test database
    with admin_engine.connect() as conn:
        # Drop database if it exists (to ensure clean state)
        conn.execute(text(f'DROP DATABASE IF EXISTS "{test_db_name}"'))
        # Create fresh test database
        conn.execute(text(f'CREATE DATABASE "{test_db_name}"'))

    admin_engine.dispose()

    yield test_db_name

    # Clean up: drop test database
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        # Terminate active connections to test database
        conn.execute(
            text(f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{test_db_name}' AND pid <> pg_backend_pid()
        """)
        )
        # Now drop the database
        conn.execute(text(f'DROP DATABASE IF EXISTS "{test_db_name}"'))
    admin_engine.dispose()


@pytest.fixture
def db_session(test_database):
    """Create a test database session."""
    # Create engine using the test database
    # Disable prepared statements to avoid "cached plan must not change result type" errors
    # during rapid schema changes in tests
    engine = create_engine(
        f"postgresql+psycopg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{test_database}",
        connect_args={"prepare_threshold": None},
    )

    # Create all tables
    Base.metadata.create_all(engine)

    # Create session
    session_factory = sessionmaker(bind=engine)
    session = session_factory()

    try:
        yield session
    finally:
        session.rollback()
        session.close()

    # Clean up tables after test (but keep database)
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(db_session, test_database):
    """Create a test client that ensures fastapi-users uses test database."""

    from api.main import app

    # Ensure sync session commits its changes first
    db_session.commit()

    # Override the sync database session for routes that use it
    def override_get_db():
        """Override sync database session for tests."""
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Create async engine with immediate cleanup settings
    test_async_database_url = f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{test_database}"
    test_async_engine = create_async_engine(
        test_async_database_url,
        pool_pre_ping=True,
        pool_size=1,  # Minimize connections
        max_overflow=0,  # No overflow connections
        pool_recycle=300,  # Recycle connections quickly
        echo=False,
        # Force connection cleanup after each request to avoid event loop conflicts
        pool_reset_on_return="commit",
    )

    test_async_session_maker = async_sessionmaker(test_async_engine, expire_on_commit=False)

    async def override_get_async_session():
        """Override async session for tests."""
        async with test_async_session_maker() as session:
            yield session

    # Overrides
    # app.dependency_overrides[...] = ...  # noqa: ERA001

    client_instance = TestClient(app, base_url=f"http://testserver{settings.API_PREFIX}")

    yield client_instance

    # Clean up overrides and engine immediately
    app.dependency_overrides.clear()

    # Let the engine be garbage collected - explicit disposal causes event loop issues


# Async test fixtures for fastapi-users integration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_db_session(test_database) -> AsyncGenerator[AsyncSession, None]:
    """Create an async test database session for fastapi-users integration."""
    # Create async engine using the test database
    async_database_url = f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{test_database}"
    async_engine = create_async_engine(async_database_url)

    # Create all tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create async session
    async_session_maker = async_sessionmaker(bind=async_engine, expire_on_commit=False)
    session = async_session_maker()

    try:
        yield session
    finally:
        await session.rollback()
        await session.close()

        # Clean up tables after test (but keep database)
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

        await async_engine.dispose()


@pytest.fixture
async def async_client(
    async_db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for FastAPI app with database session override."""

    from api.main import app

    # Override the async session dependency for testing
    async def override_get_async_session() -> AsyncGenerator[AsyncSession, None]:
        yield async_db_session

    # Overrides
    # app.dependency_overrides[...]  # noqa: ERA001

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    # Clean up overrides
    app.dependency_overrides.clear()
