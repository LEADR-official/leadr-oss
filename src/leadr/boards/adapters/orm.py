"""Board ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import ARRAY, Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from leadr.common.orm import Base

if TYPE_CHECKING:
    from leadr.accounts.adapters.orm import AccountORM
    from leadr.boards.domain.board_template import BoardTemplate
    from leadr.games.adapters.orm import GameORM


class BoardORM(Base):
    """Board ORM model.

    Represents a leaderboard/board that belongs to a game in the database.
    Maps to the boards table with foreign keys to accounts and games, a
    unique constraint on short_code (globally unique for direct sharing),
    and a partial unique constraint on (account_id, game_id, slug) for
    active boards only.
    """

    __tablename__ = "boards"
    __table_args__ = (
        UniqueConstraint("short_code", name="uq_board_short_code"),
        Index(
            "ix_board_slug_unique_when_active",
            "account_id",
            "game_id",
            "slug",
            unique=True,
            postgresql_where="is_active = true AND deleted_at IS NULL",
        ),
    )

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
    slug: Mapped[str] = mapped_column(String, nullable=False, index=True)
    icon: Mapped[str | None] = mapped_column(String, nullable=True)
    short_code: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=sa.text("true")
    )
    sort_direction: Mapped[str] = mapped_column(String, nullable=False)
    keep_strategy: Mapped[str] = mapped_column(String, nullable=False)
    created_from_template_id: Mapped[UUID | None] = mapped_column(nullable=True, default=None)
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
    description: Mapped[str | None] = mapped_column(String, nullable=True, default=None)

    # Relationships
    account: Mapped["AccountORM"] = relationship("AccountORM")  # type: ignore[name-defined]
    game: Mapped["GameORM"] = relationship("GameORM")  # type: ignore[name-defined]


class BoardTemplateORM(Base):
    """BoardTemplate ORM model.

    Represents a template for automatically generating boards at regular intervals.
    Maps to the board_templates table with foreign keys to accounts and games.
    Uses JSONB column for config to support flexible procedural generation configuration.
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
    slug: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    name_template: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    series: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    icon: Mapped[str | None] = mapped_column(String, nullable=True)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    sort_direction: Mapped[str] = mapped_column(String, nullable=False)
    keep_strategy: Mapped[str] = mapped_column(String, nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list, server_default="{}"
    )
    repeat_interval: Mapped[str] = mapped_column(String, nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=sa.text("true")
    )

    __table_args__ = (
        # Unique series identifier per game (partial index - only when series is set)
        Index(
            "uq_board_template_game_series",
            "game_id",
            "series",
            unique=True,
            postgresql_where=sa.text("series IS NOT NULL"),
        ),
    )

    # Relationships
    account: Mapped["AccountORM"] = relationship("AccountORM")  # type: ignore[name-defined]
    game: Mapped["GameORM"] = relationship("GameORM")  # type: ignore[name-defined]

    def to_domain(self) -> "BoardTemplate":
        """Convert ORM model to domain entity.

        Returns:
            BoardTemplate domain entity with all fields populated from ORM model.
        """
        from leadr.boards.domain.board import KeepStrategy, SortDirection
        from leadr.boards.domain.board_template import BoardTemplate
        from leadr.common.domain.ids import AccountID, BoardTemplateID, GameID

        return BoardTemplate(
            id=BoardTemplateID(self.id),
            account_id=AccountID(self.account_id),
            game_id=GameID(self.game_id),
            name=self.name,
            slug=self.slug,
            name_template=self.name_template,
            series=self.series,
            icon=self.icon,
            unit=self.unit,
            sort_direction=SortDirection(self.sort_direction),
            keep_strategy=KeepStrategy(self.keep_strategy),
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            tags=self.tags,
            repeat_interval=self.repeat_interval,
            config=self.config,
            next_run_at=self.next_run_at,
            is_active=self.is_active,
            is_published=self.is_published,
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

        return cls(
            id=entity.id.uuid,
            account_id=entity.account_id.uuid,
            game_id=entity.game_id.uuid,
            name=entity.name,
            slug=entity.slug,
            name_template=entity.name_template,
            series=entity.series,
            icon=entity.icon,
            unit=entity.unit,
            sort_direction=entity.sort_direction.value,
            keep_strategy=entity.keep_strategy.value,
            starts_at=entity.starts_at,
            ends_at=entity.ends_at,
            tags=entity.tags,
            repeat_interval=entity.repeat_interval,
            config=entity.config,
            next_run_at=entity.next_run_at,
            is_active=entity.is_active,
            is_published=entity.is_published,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )
