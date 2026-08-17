"""Board ORM model."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from leadr.common.orm import Base


class BoardTypeEnum(str, enum.Enum):
    """Board type enum for database."""

    RUN_IDENTITY = "RUN_IDENTITY"
    RUN_RUNS = "RUN_RUNS"
    COUNTER = "COUNTER"
    RATIO = "RATIO"


class KeepStrategyEnum(str, enum.Enum):
    """Keep strategy enum for database."""

    FIRST = "FIRST"
    BEST = "BEST"
    LATEST = "LATEST"
    NA = "NA"


class ZeroDenominatorPolicyEnum(str, enum.Enum):
    """Zero denominator policy enum for database."""

    NULL = "NULL"
    ZERO = "ZERO"
    INFINITY = "INFINITY"


class RatioDisplayEnum(str, enum.Enum):
    """Ratio display enum for database."""

    RAW = "RAW"
    PERCENT = "PERCENT"


class TieBreakerEnum(str, enum.Enum):
    """Tie breaker enum for database."""

    NUMERATOR_DESC_DENOMINATOR_ASC = "NUMERATOR_DESC_DENOMINATOR_ASC"


if TYPE_CHECKING:
    from leadr.accounts.adapters.orm import AccountORM
    from leadr.auth.adapters.orm import IdentityORM
    from leadr.boards.domain.board_template import BoardTemplate
    from leadr.games.adapters.orm import GameORM
    from leadr.scores.adapters.orm import ScoreEventORM


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
        Index("ix_boards_account_deleted_created", "account_id", "deleted_at", "created_at", "id"),
        Index("ix_boards_account_deleted_updated", "account_id", "deleted_at", "updated_at", "id"),
        Index(
            "ix_boards_account_game_deleted_created",
            "account_id",
            "game_id",
            "deleted_at",
            "created_at",
            "id",
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
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    is_published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=sa.text("true"), index=True
    )
    unique_player_names: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=sa.text("false")
    )
    sort_direction: Mapped[str] = mapped_column(String, nullable=False)
    board_type: Mapped[BoardTypeEnum] = mapped_column(
        Enum(
            BoardTypeEnum,
            name="board_type",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
            create_constraint=False,
        ),
        nullable=False,
        default=BoardTypeEnum.RUN_IDENTITY,
        server_default="RUN_IDENTITY",
    )
    keep_strategy: Mapped[KeepStrategyEnum] = mapped_column(
        Enum(
            KeepStrategyEnum,
            name="keep_strategy",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
            create_constraint=False,
        ),
        nullable=False,
        default=KeepStrategyEnum.BEST,
        server_default="BEST",
    )
    created_from_template_id: Mapped[UUID | None] = mapped_column(
        nullable=True, default=None, index=True
    )
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
    board_type: Mapped[BoardTypeEnum] = mapped_column(
        Enum(
            BoardTypeEnum,
            name="board_type",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
            create_constraint=False,
        ),
        nullable=False,
        default=BoardTypeEnum.RUN_IDENTITY,
        server_default="RUN_IDENTITY",
    )
    keep_strategy: Mapped[KeepStrategyEnum] = mapped_column(
        Enum(
            KeepStrategyEnum,
            name="keep_strategy",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
            create_constraint=False,
        ),
        nullable=False,
        default=KeepStrategyEnum.BEST,
        server_default="BEST",
    )
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
    next_run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    is_published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=sa.text("true")
    )
    unique_player_names: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=sa.text("false")
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
        Index(
            "ix_board_templates_account_deleted_created",
            "account_id",
            "deleted_at",
            "created_at",
            "id",
        ),
        Index(
            "ix_board_templates_account_deleted_updated",
            "account_id",
            "deleted_at",
            "updated_at",
            "id",
        ),
        Index(
            "ix_board_templates_account_game_deleted_created",
            "account_id",
            "game_id",
            "deleted_at",
            "created_at",
            "id",
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
        from leadr.boards.domain.board import (  # noqa: PLC0415
            BoardType,
            KeepStrategy,
            SortDirection,
        )
        from leadr.boards.domain.board_template import BoardTemplate  # noqa: PLC0415
        from leadr.common.domain.ids import AccountID, BoardTemplateID, GameID  # noqa: PLC0415

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
            board_type=BoardType(self.board_type.value),
            keep_strategy=KeepStrategy(self.keep_strategy.value),
            starts_at=self.starts_at,
            ends_at=self.ends_at,
            tags=self.tags,
            repeat_interval=self.repeat_interval,
            config=self.config,
            next_run_at=self.next_run_at,
            is_active=self.is_active,
            is_published=self.is_published,
            unique_player_names=self.unique_player_names,
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
            board_type=BoardTypeEnum(entity.board_type.value),
            keep_strategy=KeepStrategyEnum(entity.keep_strategy.value),
            starts_at=entity.starts_at,
            ends_at=entity.ends_at,
            tags=entity.tags,
            repeat_interval=entity.repeat_interval,
            config=entity.config,
            next_run_at=entity.next_run_at,
            is_active=entity.is_active,
            is_published=entity.is_published,
            unique_player_names=entity.unique_player_names,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )


class BoardStateORM(Base):
    """Board state ORM model.

    Represents the materialized ranking state for a single identity on a single board.
    Maps to the board_states table with foreign keys to boards and identities.
    The primary_value can be NULL for non-rankable entries.

    Denormalized fields (from Identity and ScoreEvent) are stored for query efficiency.
    """

    __tablename__ = "board_states"
    __table_args__ = (
        # Unique constraint: one state per board per identity
        UniqueConstraint("board_id", "identity_id", name="uq_board_state_board_identity"),
        # Index for efficient ranking queries (ordered by value, then by updated_at for ties)
        Index(
            "ix_board_states_ranking",
            "board_id",
            "primary_value",
            "updated_at",
            "id",
            postgresql_where="deleted_at IS NULL AND primary_value IS NOT NULL",
        ),
        # Index for efficient player name uniqueness checks (case-insensitive)
        Index(
            "ix_board_states_board_id_player_name_lower",
            "board_id",
            func.lower(sa.column("player_name")),
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    board_id: Mapped[UUID] = mapped_column(
        ForeignKey("boards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    identity_id: Mapped[UUID] = mapped_column(
        ForeignKey("identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    primary_value: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    aux: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, default=None)

    # Denormalized fields for query efficiency
    player_name: Mapped[str] = mapped_column(String, nullable=False, default="", server_default="")
    is_test: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=sa.text("false")
    )
    timezone: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    country: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    city: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    value_display: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    state_metadata: Mapped[Any | None] = mapped_column(
        "state_metadata", JSONB, nullable=True, default=None
    )

    # Relationships
    board: Mapped["BoardORM"] = relationship("BoardORM")  # type: ignore[name-defined]
    identity: Mapped["IdentityORM"] = relationship("IdentityORM")  # type: ignore[name-defined]


class RunEntryORM(Base):
    """Run entry ORM model.

    Represents a single scored run entry for RUN_RUNS boards where every
    submission is ranked. Maps to the run_entries table with foreign keys
    to boards, identities, and score_events.

    Denormalized fields (from Identity and ScoreEvent) are stored for query efficiency.
    """

    __tablename__ = "run_entries"
    __table_args__ = (
        # Unique constraint: one entry per board per score event
        UniqueConstraint("board_id", "score_event_id", name="uq_run_entry_board_score_event"),
        # Index for efficient ranking queries (ordered by value, then by created_at for ties)
        Index(
            "ix_run_entries_ranking",
            "board_id",
            "primary_value",
            "created_at",
            "id",
            postgresql_where="deleted_at IS NULL",
        ),
        # Index for efficient player name uniqueness checks (case-insensitive)
        Index(
            "ix_run_entries_board_id_player_name_lower",
            "board_id",
            func.lower(sa.column("player_name")),
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    board_id: Mapped[UUID] = mapped_column(
        ForeignKey("boards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    identity_id: Mapped[UUID] = mapped_column(
        ForeignKey("identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score_event_id: Mapped[UUID] = mapped_column(
        ForeignKey("score_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    primary_value: Mapped[float] = mapped_column(Float, nullable=False)

    # Denormalized fields for query efficiency
    player_name: Mapped[str] = mapped_column(String, nullable=False, default="", server_default="")
    is_test: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=sa.text("false")
    )
    timezone: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    country: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    city: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    value_display: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    entry_metadata: Mapped[Any | None] = mapped_column(
        "entry_metadata", JSONB, nullable=True, default=None
    )

    # Exclusion fields (set when entry is excluded from ranking by anti-cheat moderation)
    excluded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    excluded_reason: Mapped[str | None] = mapped_column(String, nullable=True, default=None)

    # Relationships
    board: Mapped["BoardORM"] = relationship("BoardORM")  # type: ignore[name-defined]
    identity: Mapped["IdentityORM"] = relationship("IdentityORM")  # type: ignore[name-defined]
    score_event: Mapped["ScoreEventORM"] = relationship("ScoreEventORM")  # type: ignore[name-defined]


class BoardRatioConfigORM(Base):
    """Board ratio config ORM model.

    Stores configuration for RATIO board types that derive their ranking
    from two other boards (numerator and denominator). Maps to the
    board_ratio_configs table with foreign keys to boards.
    """

    __tablename__ = "board_ratio_configs"
    __table_args__ = (
        # Only one ratio config per board
        UniqueConstraint("board_id", name="uq_board_ratio_config_board"),
    )

    board_id: Mapped[UUID] = mapped_column(
        ForeignKey("boards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    numerator_board_id: Mapped[UUID] = mapped_column(
        ForeignKey("boards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    denominator_board_id: Mapped[UUID] = mapped_column(
        ForeignKey("boards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    zero_denominator_policy: Mapped[ZeroDenominatorPolicyEnum] = mapped_column(
        Enum(
            ZeroDenominatorPolicyEnum,
            name="zero_denominator_policy",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
            create_constraint=False,
        ),
        nullable=False,
        default=ZeroDenominatorPolicyEnum.NULL,
        server_default="NULL",
    )
    min_denominator: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    min_numerator: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    scale: Mapped[int] = mapped_column(Integer, nullable=False, default=1_000_000)
    display: Mapped[RatioDisplayEnum] = mapped_column(
        Enum(
            RatioDisplayEnum,
            name="ratio_display",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
            create_constraint=False,
        ),
        nullable=False,
        default=RatioDisplayEnum.RAW,
        server_default="RAW",
    )
    decimals: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    tie_breaker: Mapped[TieBreakerEnum] = mapped_column(
        Enum(
            TieBreakerEnum,
            name="tie_breaker",
            native_enum=True,
            values_callable=lambda x: [e.value for e in x],
            create_constraint=False,
        ),
        nullable=False,
        default=TieBreakerEnum.NUMERATOR_DESC_DENOMINATOR_ASC,
        server_default="NUMERATOR_DESC_DENOMINATOR_ASC",
    )

    # Relationships
    board: Mapped["BoardORM"] = relationship("BoardORM", foreign_keys=[board_id])  # type: ignore[name-defined]
    numerator_board: Mapped["BoardORM"] = relationship(
        "BoardORM", foreign_keys=[numerator_board_id]
    )  # type: ignore[name-defined]
    denominator_board: Mapped["BoardORM"] = relationship(
        "BoardORM", foreign_keys=[denominator_board_id]
    )  # type: ignore[name-defined]
