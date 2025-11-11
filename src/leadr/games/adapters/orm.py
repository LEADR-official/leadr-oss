"""Game ORM model."""

from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from leadr.common.orm import Base


class GameORM(Base):
    """Game ORM model.

    Represents a game that belongs to an account in the database.
    Maps to the games table with foreign key to accounts and unique
    constraint on (account_id, name) to prevent duplicate game names
    within the same account.
    """

    __tablename__ = "games"
    __table_args__ = (UniqueConstraint("account_id", "name", name="uq_account_game_name"),)

    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    steam_app_id: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    default_board_id: Mapped[UUID | None] = mapped_column(nullable=True, default=None)

    # Relationships
    account: Mapped["AccountORM"] = relationship("AccountORM")  # type: ignore[name-defined]
