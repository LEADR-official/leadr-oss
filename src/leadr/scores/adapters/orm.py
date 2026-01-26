"""Score ORM models."""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from leadr.common.domain.ids import (
    BoardID,
    IdentityID,
    ScoreEventID,
    ScoreFlagID,
    ScoreSubmissionMetaID,
    UserID,
)
from leadr.common.orm import Base, ImmutableBase
from leadr.scores.domain.anti_cheat.enums import (
    FlagConfidence,
    FlagType,
    ScoreFlagStatus,
)
from leadr.scores.domain.anti_cheat.models import ScoreFlag

if TYPE_CHECKING:
    from leadr.accounts.adapters.orm import AccountORM
    from leadr.auth.adapters.orm import IdentityORM
    from leadr.boards.adapters.orm import BoardORM
    from leadr.games.adapters.orm import GameORM
    from leadr.scores.domain.anti_cheat.models import ScoreFlag, ScoreSubmissionMeta


class ScoreEventORM(ImmutableBase):
    """Score event ORM model for append-only event sourcing.

    Represents an immutable fact about a score submission in the database.
    ScoreEvents are never updated or deleted - they are append-only.
    Maps to the score_events table with foreign keys to accounts, games, boards, and identities.
    """

    __tablename__ = "score_events"

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
    identity_id: Mapped[UUID] = mapped_column(
        ForeignKey("identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    is_test: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    timezone: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    country: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    city: Mapped[str | None] = mapped_column(String, nullable=True, default=None)

    # Relationships
    account: Mapped["AccountORM"] = relationship("AccountORM")  # type: ignore[name-defined]
    game: Mapped["GameORM"] = relationship("GameORM")  # type: ignore[name-defined]
    board: Mapped["BoardORM"] = relationship("BoardORM")  # type: ignore[name-defined]
    identity: Mapped["IdentityORM"] = relationship("IdentityORM")  # type: ignore[name-defined]

    # Indexes for efficient querying
    __table_args__ = (
        # Index for listing events by board and identity
        Index("ix_score_events_board_identity", "board_id", "identity_id"),
    )


class ScoreSubmissionMetaORM(Base):
    """Score submission metadata ORM model for anti-cheat tracking.

    Tracks submission history per identity/board combination to enable
    detection of suspicious patterns like rapid-fire submissions.
    Uses identity_id as the tracking key instead of device_id, aligning with
    the event-sourcing architecture where identity is the ranking key.
    """

    __tablename__ = "score_submission_metadata"

    score_event_id: Mapped[UUID] = mapped_column(
        ForeignKey("score_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    identity_id: Mapped[UUID] = mapped_column(
        ForeignKey("identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    board_id: Mapped[UUID] = mapped_column(
        ForeignKey("boards.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    submission_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_submission_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_score_value: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)

    # Relationships
    score_event: Mapped["ScoreEventORM"] = relationship("ScoreEventORM")
    identity: Mapped["IdentityORM"] = relationship("IdentityORM")  # type: ignore[name-defined]
    board: Mapped["BoardORM"] = relationship("BoardORM")  # type: ignore[name-defined]

    # Unique constraint: one meta record per identity/board combination
    __table_args__ = (
        Index("ix_score_submission_meta_identity_board", "identity_id", "board_id", unique=True),
    )

    def to_domain(self) -> "ScoreSubmissionMeta":
        """Convert ORM model to domain entity."""
        from leadr.scores.domain.anti_cheat.models import ScoreSubmissionMeta

        return ScoreSubmissionMeta(
            id=ScoreSubmissionMetaID(self.id),
            score_event_id=ScoreEventID(self.score_event_id),
            identity_id=IdentityID(self.identity_id),
            board_id=BoardID(self.board_id),
            submission_count=self.submission_count,
            last_submission_at=self.last_submission_at,
            last_score_value=self.last_score_value,
            created_at=self.created_at,
            updated_at=self.updated_at,
            deleted_at=self.deleted_at,
        )

    @staticmethod
    def from_domain(entity: "ScoreSubmissionMeta") -> "ScoreSubmissionMetaORM":
        """Convert domain entity to ORM model."""
        return ScoreSubmissionMetaORM(
            id=entity.id.uuid,
            score_event_id=entity.score_event_id.uuid,
            identity_id=entity.identity_id.uuid,
            board_id=entity.board_id.uuid,
            submission_count=entity.submission_count,
            last_submission_at=entity.last_submission_at,
            last_score_value=entity.last_score_value,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )


class ScoreFlagORM(Base):
    """Score flag ORM model for anti-cheat detections.

    Records suspicious patterns detected by the anti-cheat system.
    Flags can be reviewed by admins to confirm or dismiss detections.
    Uses score_event_id instead of score_id, linking to the immutable
    ScoreEvent in the event-sourcing architecture.
    """

    __tablename__ = "score_flags"

    score_event_id: Mapped[UUID] = mapped_column(
        ForeignKey("score_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    flag_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    confidence: Mapped[str] = mapped_column(String, nullable=False, index=True)
    flag_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending", index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    reviewer_id: Mapped[UUID | None] = mapped_column(nullable=True, default=None)
    reviewer_decision: Mapped[str | None] = mapped_column(String, nullable=True, default=None)

    # Relationships
    score_event: Mapped["ScoreEventORM"] = relationship("ScoreEventORM")

    def to_domain(self) -> "ScoreFlag":
        """Convert ORM model to domain entity."""

        return ScoreFlag(
            id=ScoreFlagID(self.id),
            score_event_id=ScoreEventID(self.score_event_id),
            flag_type=FlagType(self.flag_type),
            confidence=FlagConfidence(self.confidence),
            metadata=self.flag_metadata,
            status=ScoreFlagStatus(self.status),
            reviewed_at=self.reviewed_at,
            reviewer_id=UserID(self.reviewer_id) if self.reviewer_id else None,
            reviewer_decision=self.reviewer_decision,
            created_at=self.created_at,
            updated_at=self.updated_at,
            deleted_at=self.deleted_at,
        )

    @staticmethod
    def from_domain(entity: "ScoreFlag") -> "ScoreFlagORM":
        """Convert domain entity to ORM model."""
        return ScoreFlagORM(
            id=entity.id.uuid,
            score_event_id=entity.score_event_id.uuid,
            flag_type=entity.flag_type.value,
            confidence=entity.confidence.value,
            flag_metadata=entity.metadata,
            status=entity.status.value,
            reviewed_at=entity.reviewed_at,
            reviewer_id=entity.reviewer_id.uuid if entity.reviewer_id else None,
            reviewer_decision=entity.reviewer_decision,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )
