"""Anti-cheat repository services."""

from typing import Any
from uuid import UUID

from pydantic import UUID4
from sqlalchemy import select

from leadr.common.repositories import BaseRepository
from leadr.scores.adapters.orm import ScoreFlagORM, ScoreSubmissionMetaORM
from leadr.scores.domain.anti_cheat.models import ScoreFlag, ScoreSubmissionMeta


class ScoreSubmissionMetaRepository(BaseRepository[ScoreSubmissionMeta, ScoreSubmissionMetaORM]):
    """Repository for managing score submission metadata persistence."""

    def _to_domain(self, orm: ScoreSubmissionMetaORM) -> ScoreSubmissionMeta:
        """Convert ORM model to domain entity."""
        return ScoreSubmissionMeta(
            id=orm.id,
            score_id=orm.score_id,
            device_id=orm.device_id,
            board_id=orm.board_id,
            submission_count=orm.submission_count,
            last_submission_at=orm.last_submission_at,
            last_score_value=orm.last_score_value,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            deleted_at=orm.deleted_at,
        )

    def _to_orm(self, entity: ScoreSubmissionMeta) -> ScoreSubmissionMetaORM:
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

    def _get_orm_class(self) -> type[ScoreSubmissionMetaORM]:
        """Get the ORM model class."""
        return ScoreSubmissionMetaORM

    async def filter(self, account_id: UUID4 | None = None, **kwargs: Any) -> list[ScoreSubmissionMeta]:
        """Filter submission metadata (not typically used for this entity).

        Args:
            account_id: Optional account ID (unused - submission meta doesn't have direct account relation)
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            Empty list (this entity uses specialized queries like get_by_device_and_board)
        """
        # This entity is typically queried via get_by_device_and_board
        # rather than filtered by account
        return []

    async def get_by_device_and_board(
        self, device_id: UUID, board_id: UUID
    ) -> ScoreSubmissionMeta | None:
        """Get submission metadata for a device/board combination.

        Args:
            device_id: ID of the device submitting scores
            board_id: ID of the board being submitted to

        Returns:
            ScoreSubmissionMeta if found, None otherwise
        """
        query = select(ScoreSubmissionMetaORM).where(
            ScoreSubmissionMetaORM.device_id == device_id,
            ScoreSubmissionMetaORM.board_id == board_id,
            ScoreSubmissionMetaORM.deleted_at.is_(None),
        )

        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()

        return self._to_domain(orm) if orm else None


class ScoreFlagRepository(BaseRepository[ScoreFlag, ScoreFlagORM]):
    """Repository for managing score flag persistence."""

    def _to_domain(self, orm: ScoreFlagORM) -> ScoreFlag:
        """Convert ORM model to domain entity."""
        from leadr.scores.domain.anti_cheat.enums import FlagConfidence, FlagType

        return ScoreFlag(
            id=orm.id,
            score_id=orm.score_id,
            flag_type=FlagType(orm.flag_type),
            confidence=FlagConfidence(orm.confidence),
            metadata=orm.flag_metadata,
            status=orm.status,
            reviewed_at=orm.reviewed_at,
            reviewer_id=orm.reviewer_id,
            reviewer_decision=orm.reviewer_decision,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            deleted_at=orm.deleted_at,
        )

    def _to_orm(self, entity: ScoreFlag) -> ScoreFlagORM:
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

    def _get_orm_class(self) -> type[ScoreFlagORM]:
        """Get the ORM model class."""
        return ScoreFlagORM

    async def filter(self, account_id: UUID4 | None = None, **kwargs: Any) -> list[ScoreFlag]:
        """Filter flags (not typically used for this entity).

        Args:
            account_id: Optional account ID (unused - flags don't have direct account relation)
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            Empty list (this entity uses specialized queries like get_flags_by_score_id, get_pending_flags)
        """
        # This entity is typically queried via get_flags_by_score_id or get_pending_flags
        # rather than filtered by account
        return []

    async def get_flags_by_score_id(self, score_id: UUID) -> list[ScoreFlag]:
        """Get all flags for a specific score.

        Args:
            score_id: ID of the score to get flags for

        Returns:
            List of flags for the score (excludes soft-deleted)
        """
        query = select(ScoreFlagORM).where(
            ScoreFlagORM.score_id == score_id,
            ScoreFlagORM.deleted_at.is_(None),
        )

        result = await self.session.execute(query)
        orms = result.scalars().all()

        return [self._to_domain(orm) for orm in orms]

    async def get_pending_flags(self) -> list[ScoreFlag]:
        """Get all pending (unreviewed) flags.

        Returns:
            List of flags with status PENDING (excludes soft-deleted)
        """
        query = select(ScoreFlagORM).where(
            ScoreFlagORM.status == "PENDING",
            ScoreFlagORM.deleted_at.is_(None),
        )

        result = await self.session.execute(query)
        orms = result.scalars().all()

        return [self._to_domain(orm) for orm in orms]
