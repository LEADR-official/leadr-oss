"""Score ORM models."""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from leadr.common.orm import Base

if TYPE_CHECKING:
    from leadr.accounts.adapters.orm import AccountORM, UserORM
    from leadr.boards.adapters.orm import BoardORM
    from leadr.games.adapters.orm import GameORM
    from leadr.scores.domain.anti_cheat.models import ScoreFlag, ScoreSubmissionMeta


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


class ScoreSubmissionMetaORM(Base):
    """Score submission metadata ORM model for anti-cheat tracking.

    Tracks submission history per device/board combination to enable
    detection of suspicious patterns like rapid-fire submissions.
    """

    __tablename__ = "score_submission_metadata"

    score_id: Mapped[UUID] = mapped_column(
        ForeignKey("scores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    board_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    submission_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_submission_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_score_value: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)

    def to_domain(self) -> "ScoreSubmissionMeta":
        """Convert ORM model to domain entity."""
        from leadr.scores.domain.anti_cheat.models import ScoreSubmissionMeta

        return ScoreSubmissionMeta(
            id=self.id,
            score_id=self.score_id,
            device_id=self.device_id,
            board_id=self.board_id,
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
            id=entity.id,
            score_id=entity.score_id,
            device_id=entity.device_id,
            board_id=entity.board_id,
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
    """

    __tablename__ = "score_flags"

    score_id: Mapped[UUID] = mapped_column(
        ForeignKey("scores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    flag_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    confidence: Mapped[str] = mapped_column(String, nullable=False, index=True)
    flag_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING", index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    reviewer_id: Mapped[UUID | None] = mapped_column(nullable=True, default=None)
    reviewer_decision: Mapped[str | None] = mapped_column(String, nullable=True, default=None)

    def to_domain(self) -> "ScoreFlag":
        """Convert ORM model to domain entity."""
        from leadr.scores.domain.anti_cheat.enums import FlagConfidence, FlagType
        from leadr.scores.domain.anti_cheat.models import ScoreFlag

        return ScoreFlag(
            id=self.id,
            score_id=self.score_id,
            flag_type=FlagType(self.flag_type),
            confidence=FlagConfidence(self.confidence),
            metadata=self.flag_metadata,
            status=self.status,
            reviewed_at=self.reviewed_at,
            reviewer_id=self.reviewer_id,
            reviewer_decision=self.reviewer_decision,
            created_at=self.created_at,
            updated_at=self.updated_at,
            deleted_at=self.deleted_at,
        )

    @staticmethod
    def from_domain(entity: "ScoreFlag") -> "ScoreFlagORM":
        """Convert domain entity to ORM model."""
        return ScoreFlagORM(
            id=entity.id,
            score_id=entity.score_id,
            flag_type=entity.flag_type.value,
            confidence=entity.confidence.value,
            flag_metadata=entity.metadata,
            status=entity.status,
            reviewed_at=entity.reviewed_at,
            reviewer_id=entity.reviewer_id,
            reviewer_decision=entity.reviewer_decision,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            deleted_at=entity.deleted_at,
        )
