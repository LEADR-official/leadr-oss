"""Board ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ARRAY, Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from leadr.common.orm import Base

if TYPE_CHECKING:
    from leadr.accounts.adapters.orm import AccountORM
    from leadr.games.adapters.orm import GameORM


class BoardORM(Base):
    """Board ORM model.

    Represents a leaderboard/board that belongs to a game in the database.
    Maps to the boards table with foreign keys to accounts and games, and a
    unique constraint on short_code (globally unique for direct sharing).
    """

    __tablename__ = "boards"
    __table_args__ = (UniqueConstraint("short_code", name="uq_board_short_code"),)

    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    game_id: Mapped[UUID] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    icon: Mapped[str] = mapped_column(String, nullable=False)
    short_code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    unit: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    sort_direction: Mapped[str] = mapped_column(String, nullable=False)
    keep_strategy: Mapped[str] = mapped_column(String, nullable=False)
    template_id: Mapped[UUID | None] = mapped_column(nullable=True, default=None)
    template_name: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list, server_default="{}"
    )

    # Relationships
    account: Mapped["AccountORM"] = relationship("AccountORM")  # type: ignore[name-defined]
    game: Mapped["GameORM"] = relationship("GameORM")  # type: ignore[name-defined]
