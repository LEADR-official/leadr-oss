"""Account and User ORM models."""

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from leadr.common.orm import Base


class AccountORM(Base):  # type: ignore[misc,valid-type]
    """Account ORM model.

    Represents an organization or team in the database.
    Maps to the accounts table with unique name and slug constraints.
    """

    __tablename__ = "accounts"

    name = Column(String, nullable=False, unique=True, index=True)
    slug = Column(String, nullable=False, unique=True, index=True)
    status = Column(String, nullable=False, default="active", server_default="active")

    # Relationships
    users = relationship("UserORM", back_populates="account", cascade="all, delete-orphan")


class UserORM(Base):  # type: ignore[misc,valid-type]
    """User ORM model.

    Represents a user within an account in the database.
    Maps to the users table with foreign key to accounts.
    """

    __tablename__ = "users"

    account_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email = Column(String, nullable=False, unique=True, index=True)
    display_name = Column(String, nullable=False)

    # Relationships
    account = relationship("AccountORM", back_populates="users")
