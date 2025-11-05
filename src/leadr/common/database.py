"""Database connection and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from leadr.config import settings


def build_database_url() -> str:
    """Build async database URL from settings."""
    return f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"


# Create async engine with connection pooling
engine = create_async_engine(
    build_database_url(),
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_POOL_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,  # Verify connections before using them
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
