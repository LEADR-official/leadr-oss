"""Common ORM base classes and utilities."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func


class TimestampMixin:
    """Mixin for automatic timestamp management."""

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.now(UTC),
    )


class UUIDMixin:
    """Mixin for UUID primary key."""

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=func.gen_random_uuid(),
    )


class BaseModel(TimestampMixin, UUIDMixin):
    """Base class for all database models with UUID primary key and timestamps."""


# Create the declarative base
Base = declarative_base(cls=BaseModel)
