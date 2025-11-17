"""Anti-cheat repository services."""

from typing import Any

from sqlalchemy import select

from leadr.common.domain.ids import (
    AccountID,
    BoardID,
    DeviceID,
    GameID,
    ScoreFlagID,
    ScoreID,
    ScoreSubmissionMetaID,
)
from leadr.common.repositories import BaseRepository
from leadr.scores.adapters.orm import ScoreFlagORM, ScoreSubmissionMetaORM
from leadr.scores.domain.anti_cheat.models import ScoreFlag, ScoreSubmissionMeta


class ScoreSubmissionMetaRepository(BaseRepository[ScoreSubmissionMeta, ScoreSubmissionMetaORM]):
    """Repository for managing score submission metadata persistence."""

    def _to_domain(self, orm: ScoreSubmissionMetaORM) -> ScoreSubmissionMeta:
        """Convert ORM model to domain entity."""
        return ScoreSubmissionMeta(
            id=ScoreSubmissionMetaID(orm.id),
            score_id=ScoreID(orm.score_id),
            device_id=DeviceID(orm.device_id),
            board_id=BoardID(orm.board_id),
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
            id=entity.id.uuid,
            score_id=entity.score_id.uuid,
            device_id=entity.device_id.uuid,
            board_id=entity.board_id.uuid,
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

    async def filter(  # type: ignore[override]
        self,
        account_id: AccountID | None = None,
        board_id: BoardID | None = None,
        device_id: DeviceID | None = None,
        **kwargs: Any,
    ) -> list[ScoreSubmissionMeta]:
        """Filter submission metadata by account and optional criteria.

        Joins with scores table to filter by account_id since submission meta doesn't have
        a direct account relation.

        Args:
            account_id: REQUIRED - Account ID to filter by (multi-tenant safety)
            board_id: Optional board ID to filter by
            device_id: Optional device ID to filter by
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            List of submission metadata for the account matching the filter criteria
        """
        from leadr.scores.adapters.orm import ScoreORM

        if account_id is None:
            msg = "account_id is required for filtering submission metadata"
            raise ValueError(msg)

        account_uuid = self._extract_uuid(account_id)
        # Join with scores table to filter by account
        query = (
            select(ScoreSubmissionMetaORM)
            .join(ScoreORM, ScoreSubmissionMetaORM.score_id == ScoreORM.id)
            .where(
                ScoreORM.account_id == account_uuid,
                ScoreSubmissionMetaORM.deleted_at.is_(None),
            )
        )

        # Apply optional filters
        if board_id is not None:
            board_uuid = self._extract_uuid(board_id)
            query = query.where(ScoreSubmissionMetaORM.board_id == board_uuid)

        if device_id is not None:
            device_uuid = self._extract_uuid(device_id)
            query = query.where(ScoreSubmissionMetaORM.device_id == device_uuid)

        result = await self.session.execute(query)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]

    async def get_by_device_and_board(
        self, device_id: DeviceID, board_id: BoardID
    ) -> ScoreSubmissionMeta | None:
        """Get submission metadata for a device/board combination.

        Args:
            device_id: ID of the device submitting scores
            board_id: ID of the board being submitted to

        Returns:
            ScoreSubmissionMeta if found, None otherwise
        """
        device_uuid = self._extract_uuid(device_id)
        board_uuid = self._extract_uuid(board_id)
        query = select(ScoreSubmissionMetaORM).where(
            ScoreSubmissionMetaORM.device_id == device_uuid,
            ScoreSubmissionMetaORM.board_id == board_uuid,
            ScoreSubmissionMetaORM.deleted_at.is_(None),
        )

        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()

        return self._to_domain(orm) if orm else None


class ScoreFlagRepository(BaseRepository[ScoreFlag, ScoreFlagORM]):
    """Repository for managing score flag persistence."""

    def _to_domain(self, orm: ScoreFlagORM) -> ScoreFlag:
        """Convert ORM model to domain entity."""
        from leadr.common.domain.ids import UserID
        from leadr.scores.domain.anti_cheat.enums import (
            FlagConfidence,
            FlagType,
            ScoreFlagStatus,
        )

        return ScoreFlag(
            id=ScoreFlagID(orm.id),
            score_id=ScoreID(orm.score_id),
            flag_type=FlagType(orm.flag_type),
            confidence=FlagConfidence(orm.confidence),
            metadata=orm.flag_metadata,
            status=ScoreFlagStatus(orm.status),
            reviewed_at=orm.reviewed_at,
            reviewer_id=UserID(orm.reviewer_id) if orm.reviewer_id else None,
            reviewer_decision=orm.reviewer_decision,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            deleted_at=orm.deleted_at,
        )

    def _to_orm(self, entity: ScoreFlag) -> ScoreFlagORM:
        """Convert domain entity to ORM model."""
        return ScoreFlagORM(
            id=entity.id.uuid,
            score_id=entity.score_id.uuid,
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

    def _get_orm_class(self) -> type[ScoreFlagORM]:
        """Get the ORM model class."""
        return ScoreFlagORM

    async def filter(  # type: ignore[override]
        self,
        account_id: AccountID | None = None,
        board_id: BoardID | None = None,
        game_id: GameID | None = None,
        status: str | None = None,
        flag_type: str | None = None,
        **kwargs: Any,
    ) -> list[ScoreFlag]:
        """Filter flags by account and optional criteria.

        Joins with scores table to filter by account_id since flags don't have
        a direct account relation.

        Args:
            account_id: REQUIRED - Account ID to filter by (multi-tenant safety)
            board_id: Optional board ID to filter by
            game_id: Optional game ID to filter by
            status: Optional status to filter by (PENDING, CONFIRMED_CHEAT, etc.)
            flag_type: Optional flag type to filter by (VELOCITY, DUPLICATE, etc.)
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            List of flags for the account matching the filter criteria
        """
        from leadr.scores.adapters.orm import ScoreORM

        if account_id is None:
            msg = "account_id is required for filtering score flags"
            raise ValueError(msg)

        account_uuid = self._extract_uuid(account_id)
        # Join with scores table to filter by account
        query = (
            select(ScoreFlagORM)
            .join(ScoreORM, ScoreFlagORM.score_id == ScoreORM.id)
            .where(
                ScoreORM.account_id == account_uuid,
                ScoreFlagORM.deleted_at.is_(None),
            )
        )

        # Apply optional filters
        if board_id is not None:
            board_uuid = self._extract_uuid(board_id)
            query = query.where(ScoreORM.board_id == board_uuid)

        if game_id is not None:
            game_uuid = self._extract_uuid(game_id)
            query = query.where(ScoreORM.game_id == game_uuid)

        if status is not None:
            query = query.where(ScoreFlagORM.status == status)

        if flag_type is not None:
            query = query.where(ScoreFlagORM.flag_type == flag_type)

        result = await self.session.execute(query)
        orms = result.scalars().all()
        return [self._to_domain(orm) for orm in orms]

    async def get_flags_by_score_id(self, score_id: ScoreID) -> list[ScoreFlag]:
        """Get all flags for a specific score.

        Args:
            score_id: ID of the score to get flags for

        Returns:
            List of flags for the score (excludes soft-deleted)
        """
        score_uuid = self._extract_uuid(score_id)
        query = select(ScoreFlagORM).where(
            ScoreFlagORM.score_id == score_uuid,
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
