"""Board ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import ARRAY, Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
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


class BoardTemplateORM(Base):
    """BoardTemplate ORM model.

    Represents a template for automatically generating boards at regular intervals.
    Maps to the board_templates table with foreign keys to accounts and games.
    Uses JSONB columns for config and config_template to support flexible configuration.
    """

    __tablename__ = "board_templates"

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
    name_template: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    repeat_interval: Mapped[str] = mapped_column(String, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    config_template: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Relationships
    account: Mapped["AccountORM"] = relationship("AccountORM")  # type: ignore[name-defined]
    game: Mapped["GameORM"] = relationship("GameORM")  # type: ignore[name-defined]

    def to_domain(self) -> "BoardTemplate":
        """Convert ORM model to domain entity.

        Returns:
            BoardTemplate domain entity with all fields populated from ORM model.
        """
        from leadr.boards.domain.board_template import BoardTemplate

        return BoardTemplate(
            id=self.id,
            account_id=self.account_id,
            game_id=self.game_id,
            name=self.name,
            name_template=self.name_template,
            repeat_interval=self.repeat_interval,
            config=self.config,
            config_template=self.config_template,
            next_run_at=self.next_run_at,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
            deleted_at=self.deleted_at,
        )

    @classmethod
    def from_domain(cls, entity: "BoardTemplate") -> "BoardTemplateORM":
        """Convert domain entity to ORM model.

        Args:
            entity: The BoardTemplate domain entity to convert.

        Returns:
            BoardTemplateORM model with all fields populated from domain entity.
        """
        from leadr.boards.domain.board_template import BoardTemplate

        return cls(
            id=entity.id,
            account_id=entity.account_id,
            game_id=entity.game_id,
            name=entity.name,
            name_template=entity.name_template,
            repeat_interval=entity.repeat_interval,
            config=entity.config,
            config_template=entity.config_template,
            next_run_at=entity.next_run_at,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )
