"""Database connection and session management."""

import ssl
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, Pool

from leadr.config import settings


def build_database_url() -> str:
    """Build async database URL from settings."""
    return f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"


def build_direct_database_url() -> str:
    """Build async database URL for direct connections (migrations).

    Uses DB_HOST_DIRECT if set, otherwise falls back to DB_HOST.
    For Neon, DB_HOST_DIRECT should be the non-pooler endpoint to avoid
    connecting through PgBouncer during migrations.
    """
    host = settings.DB_HOST_DIRECT or settings.DB_HOST
    return f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{host}:{settings.DB_PORT}/{settings.DB_NAME}"


def _get_ssl_context() -> ssl.SSLContext | None:
    """Create SSL context for production (verify-full mode).

    In production, we connect to Neon PostgreSQL which uses ISRG Root X1
    (Let's Encrypt) certificates. The system CA bundle includes this certificate,
    so we use create_default_context() which loads the system trust store.

    Returns None for DEV/TEST environments (local Postgres, no SSL needed).
    """
    if settings.ENV in ("DEV", "TEST"):
        return None
    ctx = ssl.create_default_context()
    ctx.check_hostname = True  # verify-full mode
    return ctx


def _get_connect_args() -> dict[str, Any]:
    """Get asyncpg connection arguments.

    Configures SSL and channel binding for production connections to Neon.
    Channel binding provides SCRAM-SHA-256-PLUS authentication, though asyncpg
    ignores this parameter (included for documentation/future compatibility).
    """
    args: dict[str, Any] = {}
    ssl_ctx = _get_ssl_context()
    if ssl_ctx:
        args["ssl"] = ssl_ctx
        args["channel_binding"] = "require"  # Best-effort, ignored by asyncpg
    return args


def _get_pool_class() -> type[Pool] | None:
    """Get the connection pool class based on environment.

    In production with Neon, we disable client-side pooling because Neon
    provides PgBouncer pooling on their end. Double pooling can cause
    connection management issues.

    See: https://neon.com/docs/connect/choose-connection#common-pitfalls

    Returns NullPool for production (no client pooling), None for DEV/TEST
    (use SQLAlchemy's default QueuePool).
    """
    if settings.ENV in ("DEV", "TEST"):
        return None  # Use default QueuePool
    return NullPool


def _get_pool_options() -> dict[str, Any]:
    """Get connection pool options (only used when pooling is enabled)."""
    if settings.ENV in ("DEV", "TEST"):
        return {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_POOL_MAX_OVERFLOW,
            "pool_recycle": settings.DB_POOL_RECYCLE,
            "pool_pre_ping": True,  # Verify connections before using them
        }
    return {}  # No pool options when using NullPool


# Create async engine with environment-appropriate settings
engine = create_async_engine(
    build_database_url(),
    connect_args=_get_connect_args(),
    poolclass=_get_pool_class(),
    **_get_pool_options(),
    echo=settings.DB_ECHO,  # Log SQL queries if enabled
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent lazy-loading issues after commit
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for async database session.

    The session is yielded to the caller, who is responsible for
    committing transactions explicitly. The context manager automatically
    handles cleanup and rollback on exceptions.
    """
    async with async_session_factory() as session:
        yield session
