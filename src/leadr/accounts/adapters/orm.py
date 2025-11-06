"""Account and User ORM models - STUB for RED commit."""

from datetime import datetime
from uuid import UUID

from leadr.common.orm import Base


class AccountORM(Base):  # type: ignore[misc,valid-type]
    """Account ORM model - STUB."""

    __tablename__ = "accounts"

    id: UUID
    name: str
    slug: str
    status: str
    created_at: datetime
    updated_at: datetime


class UserORM(Base):  # type: ignore[misc,valid-type]
    """User ORM model - STUB."""

    __tablename__ = "users"

    id: UUID
    account_id: UUID
    email: str
    display_name: str
    created_at: datetime
    updated_at: datetime
