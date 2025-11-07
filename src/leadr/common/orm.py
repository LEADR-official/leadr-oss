"""Common ORM base classes and utilities."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

# Define reusable mapped column types
uuid_pk = Annotated[
    UUID,
    mapped_column(primary_key=True, default=uuid4, server_default=func.gen_random_uuid()),
]

timestamp = Annotated[
    datetime,
    mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    ),
]

nullable_timestamp = Annotated[
    datetime | None,
    mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    ),
]


class Base(DeclarativeBase):
    """Base class for all database models with UUID primary key and timestamps."""

    id: Mapped[uuid_pk]
    created_at: Mapped[timestamp]
    updated_at: Mapped[timestamp] = mapped_column(onupdate=func.now())
    deleted_at: Mapped[nullable_timestamp]
