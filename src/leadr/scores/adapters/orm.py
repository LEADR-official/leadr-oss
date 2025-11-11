"""Score ORM model."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from leadr.common.orm import Base

if TYPE_CHECKING:
    from leadr.accounts.adapters.orm import AccountORM, UserORM
    from leadr.boards.adapters.orm import BoardORM
    from leadr.games.adapters.orm import GameORM


class ScoreORM(Base):
    """Score ORM model.

    Represents a player's score submission for a board in the database.
    Maps to the scores table with foreign keys to accounts, users, games, and boards.
    """

    __tablename__ = "scores"

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
    board_id: Mapped[UUID] = mapped_column(
        ForeignKey("boards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_name: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    value_display: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    filter_timezone: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    filter_country: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    filter_city: Mapped[str | None] = mapped_column(String, nullable=True, default=None)

    # Relationships
    account: Mapped["AccountORM"] = relationship("AccountORM")  # type: ignore[name-defined]
    game: Mapped["GameORM"] = relationship("GameORM")  # type: ignore[name-defined]
    board: Mapped["BoardORM"] = relationship("BoardORM")  # type: ignore[name-defined]
    user: Mapped["UserORM"] = relationship("UserORM")  # type: ignore[name-defined]
