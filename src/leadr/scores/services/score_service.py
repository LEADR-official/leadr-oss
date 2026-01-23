"""Score service for managing score operations."""

from datetime import UTC, datetime
from typing import Any

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.boards.domain.board import Board, BoardType, KeepStrategy
from leadr.boards.domain.board import SortDirection as BoardSortDirection
from leadr.boards.domain.board_state import BoardState
from leadr.boards.domain.run_entry import RunEntry
from leadr.boards.services.board_service import BoardService
from leadr.boards.services.board_state_service import BoardStateService
from leadr.boards.services.run_entry_service import RunEntryService
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import AccountID, BoardID, DeviceID, GameID, IdentityID, ScoreID
from leadr.common.domain.pagination import SortDirection, SortField
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.common.services import BaseService
from leadr.games.services.game_service import GameService
from leadr.scores.domain.anti_cheat.enums import FlagAction, ScoreStatus, TrustTier
from leadr.scores.domain.anti_cheat.models import AntiCheatResult, ScoreFlag, ScoreSubmissionMeta
from leadr.scores.domain.score import Score
from leadr.scores.domain.score_event import ScoreEvent
from leadr.scores.services.anti_cheat_repositories import (
    ScoreFlagRepository,
    ScoreSubmissionMetaRepository,
)
from leadr.scores.services.anti_cheat_service import AntiCheatService
from leadr.scores.services.repositories import ScoreRepository
from leadr.scores.services.score_event_service import ScoreEventService


class ScoreService(BaseService[Score, ScoreRepository]):
    """Service for managing score lifecycle and operations.

    This service orchestrates score creation, updates, and retrieval
    by coordinating between the domain models and repository layer.
    Ensures business rules like board/game validation are enforced.
    """

    def _create_repository(self, session: AsyncSession) -> ScoreRepository:
        """Create ScoreRepository instance."""
        return ScoreRepository(session)

    def _get_entity_name(self) -> str:
        """Get entity name for error messages."""
        return "Score"

    async def _get_active_score_for_device(
        self, account_id: AccountID, device_id: DeviceID, board_id: BoardID
    ) -> Score | None:
        """Get the active (non-deleted) score for a device on a board.

        Args:
            account_id: The account ID to filter by (multi-tenant safety).
            device_id: The device ID to search for.
            board_id: The board ID to search for.

        Returns:
            The first active Score for this device/board combo, or None.
        """
        return await self.repository.get_by_device_and_board(
            account_id=account_id,
            device_id=device_id,
            board_id=board_id,
        )

    def _is_better_score(
        self, new_value: float, existing_value: float, sort_direction: BoardSortDirection
    ) -> bool:
        """Determine if new score is better than existing based on sort direction.

        Args:
            new_value: The value of the new score.
            existing_value: The value of the existing score.
            sort_direction: The sort direction of the board.

        Returns:
            True if new score is better (should replace existing), False otherwise.
        """
        if sort_direction == BoardSortDirection.ASCENDING:
            # Lower is better for ascending (e.g., race times)
            return new_value < existing_value
        else:  # DESCENDING
            # Higher is better for descending (e.g., points/kills)
            return new_value > existing_value

    def _build_leaderboard_sort_fields(
        self, board_sort_direction: BoardSortDirection
    ) -> list[SortField]:
        """Build sort fields for leaderboard ranking based on board's sort direction.

        Args:
            board_sort_direction: The board's sort direction (ASCENDING or DESCENDING).

        Returns:
            List of SortField objects for ranking computation.
        """
        value_direction = (
            SortDirection.ASC
            if board_sort_direction == BoardSortDirection.ASCENDING
            else SortDirection.DESC
        )
        return [
            SortField(name="value", direction=value_direction),
            SortField(name="created_at", direction=SortDirection.DESC),
            SortField(name="id", direction=SortDirection.ASC),
        ]

    async def _compute_score_rank(
        self, score: Score, board_sort_direction: BoardSortDirection
    ) -> int:
        """Compute and set the rank for a score based on board's sort direction.

        Args:
            score: The score to compute rank for.
            board_sort_direction: The board's sort direction.

        Returns:
            The computed rank.
        """
        sort_fields = self._build_leaderboard_sort_fields(board_sort_direction)
        return await self.repository.get_score_rank(score, sort_fields)

    async def create_score(
        self,
        account_id: AccountID,
        game_id: GameID,
        board_id: BoardID,
        device_id: DeviceID,
        player_name: str,
        value: float,
        value_display: str | None = None,
        timezone: str | None = None,
        country: str | None = None,
        city: str | None = None,
        metadata: Any | None = None,
        is_test: bool = False,
        trust_tier: TrustTier = TrustTier.B,
        background_tasks: BackgroundTasks | None = None,
    ) -> tuple[Score, AntiCheatResult | None]:
        """Create a new score.

        Args:
            account_id: The ID of the account this score belongs to.
            game_id: The ID of the game this score belongs to.
            board_id: The ID of the board this score belongs to.
            device_id: The ID of the device that submitted this score.
            player_name: Display name of the player.
            value: Numeric value of the score for sorting/comparison.
            value_display: Optional formatted display string.
            timezone: Optional timezone filter for categorization.
            country: Optional country filter for categorization.
            city: Optional city filter for categorization.
            metadata: Optional JSON metadata for game-specific data.
            is_test: If True, marks this score as a test score.
            trust_tier: Trust tier of the device (defaults to B/medium trust).

        Returns:
            Tuple of (created Score domain entity, AntiCheatResult or None).

        Raises:
            EntityNotFoundError: If the board doesn't exist.
            ValueError: If validation fails (board doesn't belong to account,
                       game doesn't match board's game, or anti-cheat rejects submission).

        Example:
            >>> score = await service.create_score(
            ...     account_id=account.id,
            ...     game_id=game.id,
            ...     board_id=board.id,
            ...     device_id=device.id,
            ...     player_name="SpeedRunner99",
            ...     value=123.45,
            ... )
        """
        # Three-level validation:
        # 1. Validate that board exists
        board_service = BoardService(self.repository.session)
        board = await board_service.get_by_id_or_raise(board_id)

        # 2. Validate that board belongs to account
        if board.account_id != account_id:
            raise ValueError(f"Board {board_id} does not belong to account {account_id}")

        # 3. Validate that game_id matches board's game_id
        if board.game_id != game_id:
            raise ValueError(f"Game {game_id} does not match board's game {board.game_id}")

        # 4. Check keep_strategy before creating new score
        if board.keep_strategy == KeepStrategy.FIRST:
            existing_score = await self._get_active_score_for_device(
                account_id=account_id,
                device_id=device_id,
                board_id=board_id,
            )
            if existing_score is not None:
                # Return existing first score with rank, don't create new one
                existing_score.rank = await self._compute_score_rank(
                    existing_score, board.sort_direction
                )
                return existing_score, None
        elif board.keep_strategy == KeepStrategy.LATEST:
            existing_score = await self._get_active_score_for_device(
                account_id=account_id,
                device_id=device_id,
                board_id=board_id,
            )
            if existing_score is not None:
                # Soft-delete the old score before creating new one
                await self.soft_delete(existing_score.id)
        elif board.keep_strategy == KeepStrategy.BEST:
            existing_score = await self._get_active_score_for_device(
                account_id=account_id,
                device_id=device_id,
                board_id=board_id,
            )
            if existing_score is not None:
                # Check if new score is better
                is_better = self._is_better_score(value, existing_score.value, board.sort_direction)
                if not is_better:
                    # New score is worse or equal, return existing better score with rank
                    existing_score.rank = await self._compute_score_rank(
                        existing_score, board.sort_direction
                    )
                    return existing_score, None
                else:
                    # New score is better, soft-delete old one before creating new
                    await self.soft_delete(existing_score.id)

        # Create score entity (before anti-cheat so we can pass it for checking)
        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            device_id=device_id,
            player_name=player_name,
            value=value,
            value_display=value_display,
            timezone=timezone,
            country=country,
            city=city,
            metadata=metadata,
            is_test=is_test,
        )

        # Anti-cheat checking is disabled in this deprecated Score-based flow.
        # The new event-sourcing flow (submit_score) uses check_submission_for_event.
        # This entire create_score method will be removed in Phase 10 cleanup.
        # TODO: Remove this method in Phase 10
        anti_cheat_result = None
        score.activate()

        # Save score to database
        saved_score = await self.repository.create(score)

        # Compute rank for the newly created score
        saved_score.rank = await self._compute_score_rank(saved_score, board.sort_direction)

        # Schedule metadata update as background task (non-blocking)
        if background_tasks is not None:
            background_tasks.add_task(
                self.update_submission_metadata,
                saved_score,
                device_id,
                board_id,
                anti_cheat_result,
            )

        return saved_score, anti_cheat_result

    async def update_submission_metadata(
        self,
        saved_score: Score,
        device_id: DeviceID,
        board_id: BoardID,
        anti_cheat_result: AntiCheatResult | None,
    ) -> None:
        """Update submission metadata and create flags if needed.

        DEPRECATED: This method is part of the old Score-based flow and is no longer
        called since anti-cheat is disabled in create_score. It will be removed in
        Phase 10 cleanup. The new event-sourcing flow handles metadata updates
        differently.

        Args:
            saved_score: The score that was created
            device_id: ID of the device that submitted the score
            board_id: ID of the board the score was submitted to
            anti_cheat_result: Result from anti-cheat check (or None)
        """
        # Always return early since anti_cheat_result is always None in the deprecated flow
        if anti_cheat_result is None:
            return

        # TODO: Remove this entire method in Phase 10 cleanup
        # The code below is unreachable but kept for reference until cleanup
        _ = saved_score
        _ = device_id
        _ = board_id

    async def submit_score(
        self,
        board_id: BoardID,
        identity_id: IdentityID,
        value: float | None = None,
        delta: float | None = None,
        player_name: str | None = None,
        timezone: str | None = None,
        country: str | None = None,
        city: str | None = None,
        is_test: bool = False,
    ) -> tuple[ScoreEvent, BoardState | RunEntry | None, AntiCheatResult | None]:
        """Submit a score using the new event-sourcing architecture.

        This method creates a ScoreEvent and then updates the appropriate
        materialized view (BoardState or RunEntry) based on the board type.

        Args:
            board_id: The board to submit to.
            identity_id: The identity submitting the score.
            value: Score value for RUN_IDENTITY and RUN_RUNS boards.
            delta: Delta value for COUNTER boards.
            player_name: Optional display name for the player.
            timezone: Optional timezone from GeoIP.
            country: Optional country code from GeoIP.
            city: Optional city name from GeoIP.
            is_test: Whether this is a test submission.

        Returns:
            Tuple of (ScoreEvent, ranking_entry, anti_cheat_result).
            ranking_entry is BoardState for RUN_IDENTITY/COUNTER boards,
            RunEntry for RUN_RUNS boards, or None if no ranking update.

        Raises:
            ValueError: If validation fails (missing required fields, invalid board type).
            EntityNotFoundError: If board or identity doesn't exist.
        """
        # Validate board exists
        board_service = BoardService(self.repository.session)
        board = await board_service.get_by_id_or_raise(board_id)

        # Validate payload based on board type
        self._validate_submission_payload(board, value, delta)

        # Build event payload
        event_payload = self._build_event_payload(board, value, delta)

        # Create score event (always, regardless of board type)
        event_service = ScoreEventService(self.repository.session)
        event = await event_service.create_score_event(
            account_id=board.account_id,
            game_id=board.game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload=event_payload,
            is_test=is_test,
            timezone=timezone,
            country=country,
            city=city,
        )

        # TODO: Anti-cheat integration will be added in Phase 8
        anti_cheat_result: AntiCheatResult | None = None

        # Handle based on board type
        ranking_entry: BoardState | RunEntry | None = None
        if board.board_type == BoardType.RUN_IDENTITY:
            ranking_entry = await self._handle_run_identity(
                board=board,
                identity_id=identity_id,
                event=event,
                value=value,  # type: ignore[arg-type]
            )
        elif board.board_type == BoardType.RUN_RUNS:
            ranking_entry = await self._handle_run_runs(
                board=board,
                identity_id=identity_id,
                event=event,
                value=value,  # type: ignore[arg-type]
            )
        elif board.board_type == BoardType.COUNTER:
            ranking_entry = await self._handle_counter(
                board=board,
                identity_id=identity_id,
                event=event,
                delta=delta,  # type: ignore[arg-type]
            )
        # RATIO boards have no direct handler - they are derived

        return event, ranking_entry, anti_cheat_result

    def _validate_submission_payload(
        self,
        board: Board,
        value: float | None,
        delta: float | None,
    ) -> None:
        """Validate submission payload based on board type.

        Args:
            board: The board being submitted to.
            value: Score value (for RUN boards).
            delta: Delta value (for COUNTER boards).

        Raises:
            ValueError: If payload doesn't match board type requirements.
        """
        if board.board_type == BoardType.RATIO:
            raise ValueError("RATIO boards do not accept direct submissions")

        if board.board_type in (BoardType.RUN_IDENTITY, BoardType.RUN_RUNS):
            if value is None:
                raise ValueError("value is required for RUN_IDENTITY and RUN_RUNS boards")

        if board.board_type == BoardType.COUNTER:
            if delta is None:
                raise ValueError("delta is required for COUNTER boards")

    def _build_event_payload(
        self,
        board: Board,
        value: float | None,
        delta: float | None,
    ) -> dict[str, Any]:
        """Build the event payload based on board type.

        Args:
            board: The board being submitted to.
            value: Score value (for RUN boards).
            delta: Delta value (for COUNTER boards).

        Returns:
            Event payload dictionary.
        """
        if board.board_type in (BoardType.RUN_IDENTITY, BoardType.RUN_RUNS):
            return {"value": value}
        elif board.board_type == BoardType.COUNTER:
            return {"delta": delta}
        else:
            return {}

    async def _handle_run_identity(
        self,
        board: Board,
        identity_id: IdentityID,
        event: ScoreEvent,
        value: float,
    ) -> BoardState:
        """Handle RUN_IDENTITY board submission.

        Apply keep_strategy and upsert board_state.

        Args:
            board: The board.
            identity_id: The identity.
            event: The created score event.
            value: The score value.

        Returns:
            Updated or existing BoardState.
        """
        board_state_service = BoardStateService(self.repository.session)

        # Get existing state if any
        existing_state = await board_state_service.get_by_board_and_identity(
            board_id=board.id,
            identity_id=identity_id,
        )

        if existing_state is None:
            # First submission - create new state
            aux = {
                "selected_event_id": str(event.id),
                "event_count": 1,
            }
            return await board_state_service.create_board_state(
                board_id=board.id,
                identity_id=identity_id,
                primary_value=value,
                aux=aux,
            )

        # Apply keep_strategy
        event_count = (existing_state.aux or {}).get("event_count", 0) + 1

        if board.keep_strategy == KeepStrategy.FIRST:
            # Keep first score - only update event count
            aux = {
                "selected_event_id": (existing_state.aux or {}).get("selected_event_id"),
                "event_count": event_count,
            }
            return await board_state_service.upsert_board_state(
                board_id=board.id,
                identity_id=identity_id,
                primary_value=existing_state.primary_value,
                aux=aux,
            )

        if board.keep_strategy == KeepStrategy.LATEST:
            # Always use latest score
            aux = {
                "selected_event_id": str(event.id),
                "event_count": event_count,
            }
            return await board_state_service.upsert_board_state(
                board_id=board.id,
                identity_id=identity_id,
                primary_value=value,
                aux=aux,
            )

        if board.keep_strategy == KeepStrategy.BEST:
            # Keep better score based on sort direction
            existing_value = existing_state.primary_value or 0.0
            is_better = self._is_better_score(value, existing_value, board.sort_direction)

            if is_better:
                aux = {
                    "selected_event_id": str(event.id),
                    "event_count": event_count,
                }
                return await board_state_service.upsert_board_state(
                    board_id=board.id,
                    identity_id=identity_id,
                    primary_value=value,
                    aux=aux,
                )
            else:
                # Keep existing better score, just update event count
                aux = {
                    "selected_event_id": (existing_state.aux or {}).get("selected_event_id"),
                    "event_count": event_count,
                }
                return await board_state_service.upsert_board_state(
                    board_id=board.id,
                    identity_id=identity_id,
                    primary_value=existing_state.primary_value,
                    aux=aux,
                )

        # Fallback (shouldn't reach here with valid keep_strategy)
        return existing_state

    async def _handle_run_runs(
        self,
        board: Board,
        identity_id: IdentityID,
        event: ScoreEvent,
        value: float,
    ) -> RunEntry:
        """Handle RUN_RUNS board submission.

        Create a new run entry for each submission.

        Args:
            board: The board.
            identity_id: The identity.
            event: The created score event.
            value: The score value.

        Returns:
            Created RunEntry.
        """
        run_entry_service = RunEntryService(self.repository.session)
        return await run_entry_service.create_run_entry(
            board_id=board.id,
            identity_id=identity_id,
            score_event_id=event.id,
            primary_value=value,
        )

    async def _handle_counter(
        self,
        board: Board,
        identity_id: IdentityID,
        event: ScoreEvent,
        delta: float,
    ) -> BoardState:
        """Handle COUNTER board submission.

        Accumulate delta into board_state.

        Args:
            board: The board.
            identity_id: The identity.
            event: The created score event.
            delta: The delta value to accumulate.

        Returns:
            Updated BoardState.
        """
        board_state_service = BoardStateService(self.repository.session)

        # Get existing state if any
        existing_state = await board_state_service.get_by_board_and_identity(
            board_id=board.id,
            identity_id=identity_id,
        )

        if existing_state is None:
            # First submission
            aux = {
                "event_count": 1,
                "last_event_id": str(event.id),
            }
            return await board_state_service.create_board_state(
                board_id=board.id,
                identity_id=identity_id,
                primary_value=delta,
                aux=aux,
            )

        # Accumulate delta
        current_value = existing_state.primary_value or 0.0
        new_value = current_value + delta
        event_count = (existing_state.aux or {}).get("event_count", 0) + 1

        aux = {
            "event_count": event_count,
            "last_event_id": str(event.id),
        }
        return await board_state_service.upsert_board_state(
            board_id=board.id,
            identity_id=identity_id,
            primary_value=new_value,
            aux=aux,
        )

    async def get_score(self, score_id: ScoreID) -> Score | None:
        """Get a score by its ID.

        Args:
            score_id: The ID of the score to retrieve.

        Returns:
            The Score domain entity if found, None otherwise.
        """
        return await self.get_by_id(score_id)

    async def get_score_with_rank(self, score_id: ScoreID) -> Score:
        """Get a score with its rank computed.

        The rank is computed using the score's board's sort direction.
        This method is suitable for single score lookups where you need
        to know the score's position in the leaderboard.

        Args:
            score_id: The ID of the score to retrieve.

        Returns:
            The Score domain entity with rank populated.

        Raises:
            EntityNotFoundError: If the score doesn't exist.
        """
        score = await self.get_by_id_or_raise(score_id)

        # Get board's sort direction
        board_service = BoardService(self.repository.session)
        board = await board_service.get_by_id_or_raise(score.board_id)

        # Compute rank using helper
        score.rank = await self._compute_score_rank(score, board.sort_direction)
        return score

    async def list_scores(
        self,
        account_id: AccountID | None,
        board_id: BoardID | None = None,
        game_id: GameID | None = None,
        device_id: DeviceID | None = None,
        is_test: bool | None = None,
        *,
        pagination: PaginationParams,
        around_score_id: ScoreID | None = None,
        around_score_value: float | None = None,
    ) -> PaginatedResult[Score]:
        """List scores for an account with optional filters and pagination.

        Args:
            account_id: Account ID to filter by. If None, returns all scores
                (superadmin use case).
            board_id: Optional board ID to filter by.
            game_id: Optional game ID to filter by.
            device_id: Optional device ID to filter by.
            is_test: Optional filter for test scores. True returns only test scores,
                False returns only production scores, None returns all scores.
            pagination: Pagination parameters (required).
            around_score_id: Optional score ID to center results around. When provided,
                returns a window of scores centered on this score. Mutually exclusive
                with cursor pagination and around_score_value.
            around_score_value: Optional value to center results around. Returns a
                placeholder score with is_placeholder=True at the appropriate position.
                Mutually exclusive with cursor pagination and around_score_id.

        Returns:
            PaginatedResult containing scores.

        Raises:
            EntityNotFoundError: If around_score_id is provided but score doesn't exist.
            ValueError: If around_score_id score doesn't belong to the specified board_id.
        """
        # Handle around_score_id: fetch and validate target score
        around_score: Score | None = None
        if around_score_id is not None:
            around_score = await self.get_by_id_or_raise(around_score_id)

            # Validate that the score belongs to the specified board (if board_id provided)
            if board_id is not None and around_score.board_id != board_id:
                raise ValueError(f"Score {around_score_id} does not belong to board {board_id}")

            # Use the score's board for sort direction
            board_service = BoardService(self.repository.session)
            board = await board_service.get_by_id(around_score.board_id)
            if board is not None:
                # Convert board's sort direction to pagination sort direction
                value_direction = (
                    SortDirection.ASC
                    if board.sort_direction == BoardSortDirection.ASCENDING
                    else SortDirection.DESC
                )
                pagination.sort_spec = [
                    SortField(name="value", direction=value_direction),
                    SortField(name="created_at", direction=SortDirection.DESC),
                    SortField(name="id", direction=SortDirection.ASC),
                ]

        # Handle around_score_value: fetch board and set sort direction
        elif around_score_value is not None and board_id is not None:
            board_service = BoardService(self.repository.session)
            board = await board_service.get_by_id_or_raise(board_id)

            # Convert board's sort direction to pagination sort direction
            value_direction = (
                SortDirection.ASC
                if board.sort_direction == BoardSortDirection.ASCENDING
                else SortDirection.DESC
            )
            pagination.sort_spec = [
                SortField(name="value", direction=value_direction),
                SortField(name="created_at", direction=SortDirection.DESC),
                SortField(name="id", direction=SortDirection.ASC),
            ]

            # Pass board to repository for placeholder creation
            return await self.repository.filter(
                account_id=account_id,
                board_id=board_id,
                game_id=game_id,
                device_id=device_id,
                is_test=is_test,
                pagination=pagination,
                around_score_value=around_score_value,
                around_value_board=board,
            )

        # Apply board's default sort if filtering by board and no explicit sort provided
        elif board_id is not None and not pagination._user_provided_sort:
            board_service = BoardService(self.repository.session)
            board = await board_service.get_by_id(board_id)
            if board is not None:
                # Convert board's sort direction to pagination sort direction
                value_direction = (
                    SortDirection.ASC
                    if board.sort_direction == BoardSortDirection.ASCENDING
                    else SortDirection.DESC
                )
                pagination.sort_spec = [
                    SortField(name="value", direction=value_direction),
                    SortField(name="created_at", direction=SortDirection.DESC),
                    SortField(name="id", direction=SortDirection.ASC),
                ]

        return await self.repository.filter(
            account_id=account_id,
            board_id=board_id,
            game_id=game_id,
            device_id=device_id,
            is_test=is_test,
            pagination=pagination,
            around_score=around_score,
        )

    async def update_score(self, score_id: ScoreID, **updates: Any) -> Score:
        """Update a score's mutable fields.

        Accepts any fields to update as keyword arguments. Only fields
        explicitly provided will be updated, allowing null values to
        clear optional fields.

        Args:
            score_id: The ID of the score to update.
            **updates: Field names and values to update

        Returns:
            The updated Score entity.

        Raises:
            EntityNotFoundError: If the score doesn't exist.
        """
        score = await self.get_by_id_or_raise(score_id)

        for field, value in updates.items():
            setattr(score, field, value)

        return await self.repository.update(score)

    async def update_score_status(self, score_id: ScoreID, status: ScoreStatus) -> Score:
        """Update a score's status.

        Used by ScoreFlagService when admin reviews a flag to sync the
        score's status with the flag decision.

        Args:
            score_id: The ID of the score to update.
            status: New status for the score.

        Returns:
            The updated Score entity.

        Raises:
            EntityNotFoundError: If the score doesn't exist.
        """
        score = await self.get_by_id_or_raise(score_id)
        score.status = status
        return await self.repository.update(score)
