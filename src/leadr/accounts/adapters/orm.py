"""Account and User ORM models."""

import enum
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from leadr.common.orm import Base


class AccountStatusEnum(str, enum.Enum):
    """Account status enum for database."""

    ACTIVE = "active"
    SUSPENDED = "suspended"


class UserStatusEnum(str, enum.Enum):
    """User status enum for database."""

    INVITED = "invited"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class AccountORM(Base):
    """Account ORM model.

    Represents an organization or team in the database.
    Maps to the accounts table with unique name and slug constraints.
    """

    __tablename__ = "accounts"
    __table_args__ = (
        Index("ix_accounts_deleted_created", "deleted_at", "created_at", "id"),
        Index("ix_accounts_deleted_updated", "deleted_at", "updated_at", "id"),
        Index("ix_accounts_deleted_name", "deleted_at", "name", "id"),
    )

    name: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    status: Mapped[AccountStatusEnum] = mapped_column(
        Enum(
            AccountStatusEnum,
            name="account_status",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=AccountStatusEnum.ACTIVE,
        server_default="active",
        index=True,
    )
    timezone: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    country: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    city: Mapped[str | None] = mapped_column(String, nullable=True, default=None)

    # Relationships
    users: Mapped[list["UserORM"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )


class UserORM(Base):
    """User ORM model.

    Represents a user within an account in the database.
    Maps to the users table with foreign key to accounts.
    """

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_account_deleted_created", "account_id", "deleted_at", "created_at", "id"),
        Index("ix_users_account_deleted_updated", "account_id", "deleted_at", "updated_at", "id"),
    )

    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    super_admin: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false", index=True
    )
    is_owner: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false", index=True
    )
    status: Mapped[UserStatusEnum] = mapped_column(
        Enum(
            UserStatusEnum,
            name="user_status",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=UserStatusEnum.ACTIVE,
        server_default="active",
    )

    # Relationships
    account: Mapped["AccountORM"] = relationship(back_populates="users")
