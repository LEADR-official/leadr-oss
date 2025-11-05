"""Database connection and session management."""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from leadr.config import settings


def build_database_url(use_async=False) -> str:
    """Build database URL from settings."""
    return f"postgresql+{'asyncpg' if use_async else 'psycopg'}://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"


# Create engine and session factory
engine = create_engine(build_database_url())
SessionLocal = sessionmaker(bind=engine)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Get database session context manager."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database session."""
    with get_db_session() as session:
        yield session
