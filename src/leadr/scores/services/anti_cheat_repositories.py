"""Anti-cheat repository services."""

from typing import Any

from sqlalchemy import select

from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import (
    AccountID,
    BoardID,
    GameID,
    IdentityID,
    ScoreEventID,
    ScoreFlagID,
    ScoreSubmissionMetaID,
)
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.common.repositories import BaseRepository
from leadr.scores.adapters.orm import ScoreEventORM, ScoreFlagORM, ScoreSubmissionMetaORM
from leadr.scores.domain.anti_cheat.models import ScoreFlag, ScoreSubmissionMeta


class ScoreSubmissionMetaRepository(BaseRepository[ScoreSubmissionMeta, ScoreSubmissionMetaORM]):
    """Repository for managing score submission metadata persistence."""

    SORTABLE_FIELDS = {
        "id",
        "identity_id",
        "board_id",
        "submission_count",
        "last_submission_at",
        "last_score_value",
        "created_at",
        "updated_at",
    }

    def _to_domain(self, orm: ScoreSubmissionMetaORM) -> ScoreSubmissionMeta:
        """Convert ORM model to domain entity."""
        return ScoreSubmissionMeta(
            id=ScoreSubmissionMetaID(orm.id),
            score_event_id=ScoreEventID(orm.score_event_id),
            identity_id=IdentityID(orm.identity_id),
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

    def _get_orm_class(self) -> type[ScoreSubmissionMetaORM]:
        """Get the ORM model class."""
        return ScoreSubmissionMetaORM

    async def filter(
        self,
        account_id: AccountID | None = None,
        board_id: BoardID | None = None,
        identity_id: IdentityID | None = None,
        *,
        pagination: PaginationParams,
        **kwargs: Any,
    ) -> PaginatedResult[ScoreSubmissionMeta]:
        """Filter submission metadata by account and optional criteria with pagination.

        Joins with score_events table to filter by account_id since submission meta doesn't have
        a direct account relation.

        Args:
            account_id: Optional account ID to filter by. If None, returns all metadata
                (superadmin use case). Regular users should always pass account_id.
            board_id: Optional board ID to filter by
            identity_id: Optional identity ID to filter by
            pagination: Pagination parameters (required)
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            PaginatedResult containing submission metadata matching the filter criteria
        """
        # Build base query
        query = select(ScoreSubmissionMetaORM).where(ScoreSubmissionMetaORM.deleted_at.is_(None))

        # Build filters dict for cursor validation
        filters_dict: dict[str, Any] = {}

        if account_id is not None:
            account_uuid = self._extract_uuid(account_id)
            # Join with score_events table to filter by account
            query = query.join(
                ScoreEventORM, ScoreSubmissionMetaORM.score_event_id == ScoreEventORM.id
            ).where(ScoreEventORM.account_id == account_uuid)
            filters_dict["account_id"] = str(account_uuid)

        # Apply optional filters
        if board_id is not None:
            board_uuid = self._extract_uuid(board_id)
            query = query.where(ScoreSubmissionMetaORM.board_id == board_uuid)
            filters_dict["board_id"] = str(board_uuid)

        if identity_id is not None:
            identity_uuid = self._extract_uuid(identity_id)
            query = query.where(ScoreSubmissionMetaORM.identity_id == identity_uuid)
            filters_dict["identity_id"] = str(identity_uuid)

        # Validate sort fields
        for sort_field in pagination.sort_spec:
            if sort_field.name not in self.SORTABLE_FIELDS:
                raise ValueError(
                    f"Unknown sort field: {sort_field.name}. "
                    f"Valid fields: {', '.join(sorted(self.SORTABLE_FIELDS))}"
                )

        # Handle cursor if present
        cursor = None
        if pagination.has_cursor():
            cursor = pagination.decode_cursor()
            if cursor is not None:
                cursor.validate_state(pagination.sort_spec, filters_dict)

        # Execute paginated query
        return await self._execute_paginated_query(
            query=query,
            sort_fields=pagination.sort_spec,
            cursor=cursor,
            limit=pagination.limit,
        )

    async def get_by_identity_and_board(
        self, identity_id: IdentityID, board_id: BoardID
    ) -> ScoreSubmissionMeta | None:
        """Get submission metadata for an identity/board combination.

        Args:
            identity_id: ID of the identity submitting scores
            board_id: ID of the board being submitted to

        Returns:
            ScoreSubmissionMeta if found, None otherwise
        """
        identity_uuid = self._extract_uuid(identity_id)
        board_uuid = self._extract_uuid(board_id)
        query = select(ScoreSubmissionMetaORM).where(
            ScoreSubmissionMetaORM.identity_id == identity_uuid,
            ScoreSubmissionMetaORM.board_id == board_uuid,
            ScoreSubmissionMetaORM.deleted_at.is_(None),
        )

        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()

        return self._to_domain(orm) if orm else None


class ScoreFlagRepository(BaseRepository[ScoreFlag, ScoreFlagORM]):
    """Repository for managing score flag persistence."""

    SORTABLE_FIELDS = {
        "id",
        "score_event_id",
        "flag_type",
        "confidence",
        "status",
        "created_at",
        "updated_at",
    }

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
            score_event_id=ScoreEventID(orm.score_event_id),
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

    def _get_orm_class(self) -> type[ScoreFlagORM]:
        """Get the ORM model class."""
        return ScoreFlagORM

    async def filter(
        self,
        account_id: AccountID | None = None,
        board_id: BoardID | None = None,
        game_id: GameID | None = None,
        status: str | None = None,
        flag_type: str | None = None,
        *,
        pagination: PaginationParams,
        **kwargs: Any,
    ) -> PaginatedResult[ScoreFlag]:
        """Filter flags by account and optional criteria with pagination.

        Joins with score_events table to filter by account_id since flags don't have
        a direct account relation.

        Args:
            account_id: Optional account ID to filter by. If None, returns all flags
                (superadmin use case). Regular users should always pass account_id.
            board_id: Optional board ID to filter by
            game_id: Optional game ID to filter by
            status: Optional status to filter by (PENDING, CONFIRMED_CHEAT, etc.)
            flag_type: Optional flag type to filter by (VELOCITY, DUPLICATE, etc.)
            pagination: Pagination parameters (required)
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
            PaginatedResult containing flags matching the filter criteria
        """
        # Build base query
        query = select(ScoreFlagORM).where(ScoreFlagORM.deleted_at.is_(None))

        # Join with score_events table if we need to filter by account, board, or game
        needs_event_join = account_id is not None or board_id is not None or game_id is not None
        if needs_event_join:
            query = query.join(ScoreEventORM, ScoreFlagORM.score_event_id == ScoreEventORM.id)

        # Build filters dict for cursor validation
        filters_dict: dict[str, Any] = {}

        if account_id is not None:
            account_uuid = self._extract_uuid(account_id)
            query = query.where(ScoreEventORM.account_id == account_uuid)
            filters_dict["account_id"] = str(account_uuid)

        if board_id is not None:
            board_uuid = self._extract_uuid(board_id)
            query = query.where(ScoreEventORM.board_id == board_uuid)
            filters_dict["board_id"] = str(board_uuid)

        if game_id is not None:
            game_uuid = self._extract_uuid(game_id)
            query = query.where(ScoreEventORM.game_id == game_uuid)
            filters_dict["game_id"] = str(game_uuid)

        if status is not None:
            query = query.where(ScoreFlagORM.status == status)
            filters_dict["status"] = status

        if flag_type is not None:
            query = query.where(ScoreFlagORM.flag_type == flag_type)
            filters_dict["flag_type"] = flag_type

        # Validate sort fields
        for sort_field in pagination.sort_spec:
            if sort_field.name not in self.SORTABLE_FIELDS:
                raise ValueError(
                    f"Unknown sort field: {sort_field.name}. "
                    f"Valid fields: {', '.join(sorted(self.SORTABLE_FIELDS))}"
                )

        # Handle cursor if present
        cursor = None
        if pagination.has_cursor():
            cursor = pagination.decode_cursor()
            if cursor is not None:
                cursor.validate_state(pagination.sort_spec, filters_dict)

        # Execute paginated query
        return await self._execute_paginated_query(
            query=query,
            sort_fields=pagination.sort_spec,
            cursor=cursor,
            limit=pagination.limit,
        )

    async def get_flags_by_score_event_id(self, score_event_id: ScoreEventID) -> list[ScoreFlag]:
        """Get all flags for a specific score event.

        Args:
            score_event_id: ID of the score event to get flags for

        Returns:
            List of flags for the score event (excludes soft-deleted)
        """
        score_event_uuid = self._extract_uuid(score_event_id)
        query = select(ScoreFlagORM).where(
            ScoreFlagORM.score_event_id == score_event_uuid,
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
            ScoreFlagORM.status == "pending",
            ScoreFlagORM.deleted_at.is_(None),
        )

        result = await self.session.execute(query)
        orms = result.scalars().all()

        return [self._to_domain(orm) for orm in orms]
