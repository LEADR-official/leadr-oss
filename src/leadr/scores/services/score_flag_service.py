"""Score flag service for managing flag operations."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Float, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.boards.domain.board import Board, BoardType, KeepStrategy
from leadr.boards.domain.board import SortDirection as BoardSortDirection
from leadr.boards.domain.board_state import BoardState
from leadr.boards.services.board_service import BoardService
from leadr.boards.services.board_state_service import BoardStateService
from leadr.boards.services.run_entry_service import RunEntryService
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import (
    AccountID,
    BoardID,
    GameID,
    IdentityID,
    ScoreEventID,
    ScoreFlagID,
    UserID,
)
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.common.services import BaseService
from leadr.scores.adapters.orm import ScoreEventORM, ScoreFlagORM
from leadr.scores.domain.anti_cheat.enums import FlagConfidence, FlagType, ScoreFlagStatus
from leadr.scores.domain.anti_cheat.models import ScoreFlag
from leadr.scores.services.anti_cheat_repositories import ScoreFlagRepository
from leadr.scores.services.score_event_service import ScoreEventService


class ScoreFlagService(BaseService[ScoreFlag, ScoreFlagRepository]):
    """Service for managing score flag lifecycle and operations.

    This service orchestrates flag listing, retrieval, and review operations
    by coordinating between the domain models and repository layer.
    """

    def __init__(self, session: AsyncSession):
        """Initialize service with database session.

        Args:
            session: SQLAlchemy async session for database operations
        """
        super().__init__(session)
        self.session = session

    def _create_repository(self, session: AsyncSession) -> ScoreFlagRepository:
        """Create ScoreFlagRepository instance."""
        return ScoreFlagRepository(session)

    def _get_entity_name(self) -> str:
        """Get entity name for error messages."""
        return "ScoreFlag"

    async def list_flags(
        self,
        account_id: AccountID | None,
        board_id: BoardID | None = None,
        game_id: GameID | None = None,
        status: str | None = None,
        flag_type: str | None = None,
        *,
        pagination: PaginationParams,
    ) -> PaginatedResult[ScoreFlag]:
        """List score flags for an account with optional filters and pagination.

        Args:
            account_id: Account ID to filter by. If None, returns all flags
                (superadmin use case).
            board_id: Optional board ID to filter by
            game_id: Optional game ID to filter by
            status: Optional status to filter by (PENDING, CONFIRMED_CHEAT, etc.)
            flag_type: Optional flag type to filter by (VELOCITY, DUPLICATE, etc.)
            pagination: Pagination parameters (required)

        Returns:
            PaginatedResult containing flags matching the filter criteria

        Example:
            >>> flags = await service.list_flags(
            ...     account_id=account.id,
            ...     status="pending",
            ...     pagination=PaginationParams(cursor=None, limit=100, sort=None),
            ... )
        """
        return await self.repository.filter(
            account_id=account_id,
            board_id=board_id,
            game_id=game_id,
            status=status,
            flag_type=flag_type,
            pagination=pagination,
        )

    async def get_flag(self, flag_id: ScoreFlagID) -> ScoreFlag | None:
        """Get a flag by its ID.

        Args:
            flag_id: The ID of the flag to retrieve

        Returns:
            The flag if found, None otherwise

        Example:
            >>> flag = await service.get_flag(flag_id)
        """
        return await self.get_by_id(flag_id)

    async def create_flag(
        self,
        score_event_id: ScoreEventID,
        flag_type: FlagType,
        confidence: FlagConfidence,
        status: ScoreFlagStatus = ScoreFlagStatus.PENDING,
        metadata: dict[str, Any] | None = None,
    ) -> ScoreFlag:
        """Create a new score flag (for manual admin flagging).

        Args:
            score_event_id: ID of the score event to flag
            flag_type: Type of flag (MANUAL, DUPLICATE, etc.)
            confidence: Confidence level (LOW, MEDIUM, HIGH)
            status: Initial status (defaults to PENDING)
            metadata: Optional metadata/notes about the flag

        Returns:
            The created ScoreFlag

        Example:
            >>> flag = await service.create_flag(
            ...     score_event_id=event.id,
            ...     flag_type=FlagType.MANUAL,
            ...     confidence=FlagConfidence.MEDIUM,
            ...     metadata={"reason": "Suspicious score"},
            ... )
        """
        flag = ScoreFlag(
            score_event_id=score_event_id,
            flag_type=flag_type,
            confidence=confidence,
            metadata=metadata or {},
            status=status,
        )
        created_flag = await self.repository.create(flag)

        # Sync ranking if status requires exclusion (for manual admin flagging flow)
        if status in (ScoreFlagStatus.CONFIRMED_CHEAT, ScoreFlagStatus.REMOVED):
            await self._sync_ranking_status(created_flag, status)

        return created_flag

    async def _sync_ranking_status(self, flag: ScoreFlag, new_flag_status: ScoreFlagStatus) -> None:
        """Sync ranking status based on flag status change.

        When a flag is reviewed, the ranking should be updated:
        - CONFIRMED_CHEAT → Exclude from ranking (set excluded_at on run_entry or recompute)
        - FALSE_POSITIVE or DISMISSED → Restore to ranking if needed

        Args:
            flag: The flag being reviewed (contains score_event_id)
            new_flag_status: The new status being set on the flag
        """
        # Get the score event
        event_service = ScoreEventService(self.session)
        event = await event_service.get_score_event(flag.score_event_id)
        if event is None:
            return

        # Get the board to determine type
        board_service = BoardService(self.session)
        board = await board_service.get_board(event.board_id)
        if board is None:
            return

        is_exclusion = new_flag_status in (
            ScoreFlagStatus.CONFIRMED_CHEAT,
            ScoreFlagStatus.REMOVED,
        )
        is_restoration = new_flag_status in (
            ScoreFlagStatus.FALSE_POSITIVE,
            ScoreFlagStatus.DISMISSED,
        )

        if not is_exclusion and not is_restoration:
            # Status is PENDING or unknown - no action needed
            return

        if board.board_type == BoardType.RUN_RUNS:
            await self._sync_run_runs_entry(
                board_id=board.id,
                score_event_id=flag.score_event_id,
                exclude=is_exclusion,
                flag_status=new_flag_status,
            )
        elif board.board_type == BoardType.RUN_IDENTITY:
            await self._sync_run_identity_state(
                board=board,
                identity_id=event.identity_id,
                flagged_event_id=flag.score_event_id,
            )
        elif board.board_type == BoardType.COUNTER:
            await self._sync_counter_state(
                board=board,
                identity_id=event.identity_id,
            )

        # Trigger ratio recomputes if needed
        if board.board_type in (BoardType.RUN_IDENTITY, BoardType.COUNTER):
            await self._sync_ratio_dependents(board.id, event.identity_id)

    async def _sync_run_runs_entry(
        self,
        board_id: BoardID,
        score_event_id: ScoreEventID,
        exclude: bool,
        flag_status: ScoreFlagStatus,
    ) -> None:
        """Exclude or restore a run entry from rankings.

        Args:
            board_id: Board ID
            score_event_id: Score event ID
            exclude: True to exclude, False to restore
            flag_status: The flag status that triggered this sync
        """
        run_entry_service = RunEntryService(self.session)
        entry = await run_entry_service.get_by_board_and_score_event(board_id, score_event_id)
        if entry is None:
            return  # No entry exists (rejected at ingest)

        if exclude:
            entry.excluded_at = datetime.now(UTC)
            entry.excluded_reason = flag_status.value
        else:
            entry.excluded_at = None
            entry.excluded_reason = None

        await run_entry_service.repository.update(entry)

    async def _sync_run_identity_state(
        self,
        board: Board,
        identity_id: IdentityID,
        flagged_event_id: ScoreEventID,
    ) -> None:
        """Recompute board state for a RUN_IDENTITY board after flag status change.

        Only recomputes if the flagged event was the currently selected event.

        Args:
            board: The board
            identity_id: Identity whose state may need recomputation
            flagged_event_id: The flagged score event ID
        """
        board_state_service = BoardStateService(self.session)
        state = await board_state_service.get_by_board_and_identity(board.id, identity_id)
        if state is None:
            return

        # Check if the flagged event is the currently selected event
        selected_event_id = (state.aux or {}).get("selected_event_id")
        if selected_event_id != str(flagged_event_id):
            return  # Flagged event is not the selected one, no recomputation needed

        # Recompute by finding the next eligible event
        await self._recompute_run_identity(board, identity_id, state)

    async def _recompute_run_identity(
        self,
        board: Board,
        identity_id: IdentityID,
        existing_state: BoardState,
    ) -> None:
        """Recompute RUN_IDENTITY state by finding the next eligible event.

        Queries all score events for this identity+board, excludes those with
        CONFIRMED_CHEAT flags, and selects the best one based on keep_strategy.

        Args:
            board: The board configuration
            identity_id: Identity to recompute for
            existing_state: Existing board state to update
        """
        board_state_service = BoardStateService(self.session)

        # Correlated subquery - only checks flags for events being queried
        # Uses NOT EXISTS for efficient early-exit evaluation
        exclusion_flag_exists = exists(
            select(ScoreFlagORM.id).where(
                ScoreFlagORM.score_event_id == ScoreEventORM.id,
                ScoreFlagORM.status.in_(
                    [
                        ScoreFlagStatus.CONFIRMED_CHEAT.value,
                        ScoreFlagStatus.REMOVED.value,
                    ]
                ),
            )
        )

        # Build ordering based on keep_strategy
        if board.keep_strategy == KeepStrategy.FIRST:
            order_by = ScoreEventORM.created_at.asc()
        elif board.keep_strategy == KeepStrategy.LATEST:
            order_by = ScoreEventORM.created_at.desc()
        elif board.keep_strategy == KeepStrategy.BEST:
            if board.sort_direction == BoardSortDirection.ASCENDING:
                # Lower is better for ascending
                order_by = func.cast(ScoreEventORM.event_payload["value"].astext, Float).asc()
            else:
                # Higher is better for descending
                order_by = func.cast(ScoreEventORM.event_payload["value"].astext, Float).desc()
        else:
            order_by = ScoreEventORM.created_at.asc()

        # Query eligible events
        query = (
            select(ScoreEventORM)
            .where(
                ScoreEventORM.board_id == board.id.uuid,
                ScoreEventORM.identity_id == identity_id.uuid,
                ~exclusion_flag_exists,
            )
            .order_by(order_by)
            .limit(1)
        )

        result = await self.session.execute(query)
        eligible_event = result.scalar_one_or_none()

        event_count = (existing_state.aux or {}).get("event_count", 1)

        if eligible_event is None:
            # No eligible event - set primary_value to NULL
            existing_state.primary_value = None
            existing_state.aux = {
                "selected_event_id": None,
                "event_count": event_count,
            }
        else:
            # Update state with new selected event
            value = eligible_event.event_payload.get("value")
            existing_state.primary_value = float(value) if value is not None else None
            existing_state.aux = {
                "selected_event_id": str(eligible_event.id),
                "event_count": event_count,
            }
            # Update denormalized fields from the new event
            existing_state.timezone = eligible_event.timezone
            existing_state.country = eligible_event.country
            existing_state.city = eligible_event.city

        await board_state_service.repository.update(existing_state)

    async def _sync_counter_state(
        self,
        board: Board,
        identity_id: IdentityID,
    ) -> None:
        """Recompute COUNTER board state excluding CONFIRMED_CHEAT events.

        Args:
            board: The board
            identity_id: Identity to recompute for
        """
        board_state_service = BoardStateService(self.session)
        state = await board_state_service.get_by_board_and_identity(board.id, identity_id)
        if state is None:
            return

        # Correlated subquery - only checks flags for events being queried
        # Uses NOT EXISTS for efficient early-exit evaluation
        exclusion_flag_exists = exists(
            select(ScoreFlagORM.id).where(
                ScoreFlagORM.score_event_id == ScoreEventORM.id,
                ScoreFlagORM.status.in_(
                    [
                        ScoreFlagStatus.CONFIRMED_CHEAT.value,
                        ScoreFlagStatus.REMOVED.value,
                    ]
                ),
            )
        )

        # Sum all deltas excluding confirmed cheats
        sum_query = select(
            func.sum(func.cast(ScoreEventORM.event_payload["delta"].astext, Float)),
            func.count(),
        ).where(
            ScoreEventORM.board_id == board.id.uuid,
            ScoreEventORM.identity_id == identity_id.uuid,
            ~exclusion_flag_exists,
        )

        result = await self.session.execute(sum_query)
        row = result.one()
        total_value = row[0]
        event_count = row[1]

        if total_value is None or event_count == 0:
            # No eligible events - set to 0
            state.primary_value = 0.0
            state.aux = {
                "event_count": 0,
            }
        else:
            state.primary_value = float(total_value)
            state.aux = {
                "event_count": event_count,
            }

        await board_state_service.repository.update(state)

    async def _sync_ratio_dependents(
        self,
        board_id: BoardID,
        identity_id: IdentityID,
    ) -> None:
        """Trigger ratio board recomputation for dependent boards.

        Args:
            board_id: The source board that was updated
            identity_id: The identity whose state was updated
        """
        state_service = BoardStateService(self.session)
        dependent_configs = await state_service.find_dependent_ratio_boards(board_id)
        for config in dependent_configs:
            await state_service.recompute_ratio_for_identity(config, identity_id)

    async def review_flag(
        self,
        flag_id: ScoreFlagID,
        status: ScoreFlagStatus,
        reviewer_decision: str | None = None,
        reviewer_id: UserID | None = None,
    ) -> ScoreFlag:
        """Review a flag and update its status.

        Note: Ranking updates for flag status changes are not yet implemented
        in the event-sourcing architecture.

        Args:
            flag_id: The ID of the flag to review
            status: New status (CONFIRMED_CHEAT, FALSE_POSITIVE, DISMISSED)
            reviewer_decision: Optional admin notes/decision
            reviewer_id: Optional ID of the reviewing admin

        Returns:
            The updated flag

        Raises:
            EntityNotFoundError: If the flag doesn't exist

        Example:
            >>> flag = await service.review_flag(
            ...     flag_id=flag.id,
            ...     status=ScoreFlagStatus.CONFIRMED_CHEAT,
            ...     reviewer_decision="Verified cheating behavior",
            ... )
        """
        flag = await self.get_by_id_or_raise(flag_id)

        # Update review fields
        flag.status = status
        flag.reviewed_at = datetime.now(UTC)
        if reviewer_decision is not None:
            flag.reviewer_decision = reviewer_decision
        if reviewer_id is not None:
            flag.reviewer_id = reviewer_id

        # Persist the flag first so ranking sync queries see the updated status
        updated_flag = await self.repository.update(flag)

        # Sync score status with flag decision (after flag is persisted)
        await self._sync_ranking_status(updated_flag, status)

        return updated_flag

    async def update_flag(self, flag_id: ScoreFlagID, **updates: Any) -> ScoreFlag:
        """Update a flag's status and/or reviewer decision.

        Accepts any fields to update as keyword arguments. Only fields
        explicitly provided will be updated, allowing null values to
        clear optional fields.

        Note: When status is updated, reviewed_at is automatically set
        to the current time.

        Args:
            flag_id: The ID of the flag to update
            **updates: Field names and values to update

        Returns:
            The updated flag

        Raises:
            EntityNotFoundError: If the flag doesn't exist

        Example:
            >>> flag = await service.update_flag(
            ...     flag_id=flag.id,
            ...     status=ScoreFlagStatus.FALSE_POSITIVE,
            ... )
        """
        flag = await self.get_by_id_or_raise(flag_id)

        # Track if we need to sync ranking after update
        new_status: ScoreFlagStatus | None = None

        # Special handling: when status is updated, also set reviewed_at
        if "status" in updates:
            updates["reviewed_at"] = datetime.now(UTC)
            new_status = updates["status"]
            if isinstance(new_status, str):
                new_status = ScoreFlagStatus(new_status)

        # Apply all updates atomically - validation runs once at the end
        flag = flag.model_copy(update=updates)

        # Persist the flag first so ranking sync queries see the updated status
        updated_flag = await self.repository.update(flag)

        # Now sync ranking status after the flag is persisted
        if new_status is not None:
            await self._sync_ranking_status(updated_flag, new_status)

        return updated_flag
