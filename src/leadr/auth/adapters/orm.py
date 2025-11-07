"""API Key ORM models."""

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from leadr.common.orm import Base


class APIKeyStatusEnum(str, enum.Enum):
    """API Key status enum for database."""

    ACTIVE = "active"
    REVOKED = "revoked"


class APIKeyORM(Base):
    """API Key ORM model.

    Represents an API key for account authentication in the database.
    Maps to the api_keys table with foreign key to accounts.
    """

    __tablename__ = "api_keys"

    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    key_hash: Mapped[str] = mapped_column(String, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    status: Mapped[APIKeyStatusEnum] = mapped_column(
        Enum(
            APIKeyStatusEnum,
            name="api_key_status",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=APIKeyStatusEnum.ACTIVE,
        server_default="active",
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
