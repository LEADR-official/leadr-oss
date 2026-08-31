"""Score service for managing score operations."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTasks

from leadr.boards.domain.board import Board, BoardType, KeepStrategy
from leadr.boards.domain.board import SortDirection as BoardSortDirection
from leadr.boards.domain.board_ratio_config import BoardRatioConfig
from leadr.boards.domain.board_state import BoardState
from leadr.boards.domain.run_entry import RunEntry
from leadr.boards.services.board_service import BoardService
from leadr.boards.services.board_state_service import BoardStateService
from leadr.boards.services.repositories import BoardStateRepository, RunEntryRepository
from leadr.boards.services.run_entry_service import RunEntryService
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.exceptions import EntityNotFoundError, PlayerNameConflictError
from leadr.common.domain.ids import (
    AccountID,
    BoardID,
    BoardStateID,
    GameID,
    IdentityID,
    RunEntryID,
    ScoreID,
)
from leadr.common.domain.pagination import SortDirection, SortField
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.config import settings
from leadr.scores.domain.anti_cheat.enums import FlagAction, TrustTier
from leadr.scores.domain.anti_cheat.models import AntiCheatResult, ScoreFlag, ScoreSubmissionMeta
from leadr.scores.domain.score_event import ScoreEvent
from leadr.scores.services.anti_cheat_repositories import (
    ScoreFlagRepository,
    ScoreSubmissionMetaRepository,
)
from leadr.scores.services.anti_cheat_service import AntiCheatService
from leadr.scores.services.score_event_service import ScoreEventService


def _normalise_player_name(name: str) -> str:
    """Normalise player name for comparison.

    - Collapses multiple whitespace to single space
    - Trims leading/trailing whitespace
    - Converts to lowercase
    """
    return " ".join(name.split()).strip().lower()


class ScoreService:
    """Service for managing score lifecycle and operations.

    This service orchestrates score submission via event-sourcing, and provides
    query methods that delegate to BoardStateService and RunEntryService for
    reading materialized ranking data.

    The Score entity has been replaced by:
    - ScoreEvent: immutable event log
    - BoardState/RunEntry: materialized ranking views

    All GET queries return BoardState or RunEntry data with IDs masked to scr_ prefix.
    """

    def __init__(self, session: AsyncSession):
        """Initialize service with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

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
        trust_tier: TrustTier = TrustTier.B,
        background_tasks: BackgroundTasks | None = None,
        value_display: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[ScoreEvent, BoardState | RunEntry | None, AntiCheatResult | None]:
        """Submit a score using the event-sourcing architecture.

        This method creates a ScoreEvent, runs anti-cheat checks, and then
        updates the appropriate materialized view (BoardState or RunEntry)
        based on the board type and anti-cheat result.

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
            trust_tier: Trust tier for anti-cheat thresholds (defaults to B).
            background_tasks: Optional BackgroundTasks for async ratio updates.
            value_display: Optional formatted display string for the score value.
            metadata: Optional custom metadata dictionary.

        Returns:
            Tuple of (ScoreEvent, ranking_entry, anti_cheat_result).
            ranking_entry is BoardState for RUN_IDENTITY/COUNTER boards,
            RunEntry for RUN_RUNS boards, or None if no ranking update
            (e.g., if anti-cheat REJECTs).

        Raises:
            ValueError: If validation fails (missing required fields, invalid board type).
            EntityNotFoundError: If board or identity doesn't exist.
        """
        # Validate board exists
        board_service = BoardService(self.session)
        board = await board_service.get_by_id_or_raise(board_id)

        # Validate payload based on board type
        self._validate_submission_payload(board, value, delta)

        # Check unique player name constraint
        if board.unique_player_names and player_name:
            await self._check_player_name_availability(board, identity_id, player_name)

        # Build event payload
        event_payload = self._build_event_payload(
            board, value, delta, value_display=value_display, metadata=metadata
        )

        # Create score event (always, regardless of anti-cheat result - immutable audit log)
        event_service = ScoreEventService(self.session)
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

        # Run anti-cheat checks (if enabled)
        anti_cheat_result: AntiCheatResult | None = None
        if settings.ANTICHEAT_ENABLED:
            anti_cheat_service = AntiCheatService(self.session)
            anti_cheat_result = await anti_cheat_service.check_submission_for_event(
                score_event=event,
                trust_tier=trust_tier,
                identity_id=identity_id,
                board_id=board_id,
            )

            # Update submission metadata for future anti-cheat checks
            await self._update_submission_metadata(
                event=event,
                identity_id=identity_id,
                board_id=board_id,
                value=value,
            )

            # Create flag if anti-cheat FLAGs the submission
            if anti_cheat_result.action == FlagAction.FLAG:
                await self._create_score_flag(event=event, result=anti_cheat_result)

            # Skip ranking update if anti-cheat REJECTs the submission
            if anti_cheat_result.action == FlagAction.REJECT:
                return event, None, anti_cheat_result

        # Handle based on board type (ACCEPT or FLAG both update rankings)
        ranking_entry: BoardState | RunEntry | None = None
        if board.board_type == BoardType.RUN_IDENTITY:
            ranking_entry = await self._handle_run_identity(
                board=board,
                identity_id=identity_id,
                event=event,
                value=value,  # type: ignore[arg-type]
                player_name=player_name or "",
                is_test=is_test,
                timezone=timezone,
                country=country,
                city=city,
                value_display=value_display,
                metadata=metadata,
            )
        elif board.board_type == BoardType.RUN_RUNS:
            ranking_entry = await self._handle_run_runs(
                board=board,
                identity_id=identity_id,
                event=event,
                value=value,  # type: ignore[arg-type]
                player_name=player_name or "",
                is_test=is_test,
                timezone=timezone,
                country=country,
                city=city,
                value_display=value_display,
                metadata=metadata,
            )
        elif board.board_type == BoardType.COUNTER:
            ranking_entry = await self._handle_counter(
                board=board,
                identity_id=identity_id,
                event=event,
                delta=delta,  # type: ignore[arg-type]
                player_name=player_name or "",
                is_test=is_test,
                timezone=timezone,
                country=country,
                city=city,
                metadata=metadata,
            )
        # RATIO boards have no direct handler - they are derived

        # Trigger ratio board updates if this board is a source for any ratio boards
        if ranking_entry is not None and background_tasks is not None:
            await self._schedule_ratio_updates(
                board_id=board_id,
                identity_id=identity_id,
                background_tasks=background_tasks,
            )

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

    async def _check_player_name_availability(
        self,
        board: Board,
        identity_id: IdentityID,
        player_name: str,
    ) -> None:
        """Check if player name is available on the board.

        Checks the appropriate table based on board type:
        - RUN_RUNS boards → RunEntry table
        - RUN_IDENTITY/COUNTER boards → BoardState table

        Args:
            board: The board to check.
            identity_id: The identity submitting (excluded from conflict check).
            player_name: The player name to check.

        Raises:
            PlayerNameConflictError: If name is taken by another identity.
        """
        normalised_name = _normalise_player_name(player_name)
        if not normalised_name:
            return  # Empty name, no conflict possible

        # Check appropriate table based on board type
        if board.board_type == BoardType.RUN_RUNS:
            repo = RunEntryRepository(self.session)
        else:  # RUN_IDENTITY, COUNTER
            repo = BoardStateRepository(self.session)

        is_available = await repo.is_player_name_available(
            board_id=board.id,
            player_name=normalised_name,
            exclude_identity_id=identity_id,
        )
        if not is_available:
            raise PlayerNameConflictError(normalised_name)

    def _build_event_payload(
        self,
        board: Board,
        value: float | None,
        delta: float | None,
        value_display: str | None = None,
        metadata: Any | None = None,
    ) -> dict[str, Any]:
        """Build the event payload based on board type.

        Args:
            board: The board being submitted to.
            value: Score value (for RUN boards).
            delta: Delta value (for COUNTER boards).
            value_display: String representation of value for display (ignored for COUNTER).
            metadata: Metadata to be associated with score event

        Returns:
            Event payload dictionary.
        """
        if board.board_type in (BoardType.RUN_IDENTITY, BoardType.RUN_RUNS):
            return {
                "value": value,
                "value_display": value_display,
                "metadata": metadata,
            }
        elif board.board_type == BoardType.COUNTER:
            return {"delta": delta, "metadata": metadata}
        else:
            return {}

    async def _handle_run_identity(
        self,
        board: Board,
        identity_id: IdentityID,
        event: ScoreEvent,
        value: float,
        player_name: str,
        is_test: bool,
        timezone: str | None,
        country: str | None,
        city: str | None,
        value_display: str | None,
        metadata: dict[str, Any] | None,
    ) -> BoardState:
        """Handle RUN_IDENTITY board submission.

        Apply keep_strategy and upsert board_state.

        Args:
            board: The board.
            identity_id: The identity.
            event: The created score event.
            value: The score value.
            player_name: Display name at submission time.
            is_test: Whether this is a test submission.
            timezone: Timezone from GeoIP.
            country: Country code from GeoIP.
            city: City name from GeoIP.
            value_display: Optional formatted display string.
            metadata: Optional custom metadata.

        Returns:
            Updated or existing BoardState.
        """
        board_state_service = BoardStateService(self.session)

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
                player_name=player_name,
                is_test=is_test,
                timezone=timezone,
                country=country,
                city=city,
                value_display=value_display,
                metadata=metadata,
            )

        # Apply keep_strategy
        event_count = (existing_state.aux or {}).get("event_count", 0) + 1

        if board.keep_strategy == KeepStrategy.FIRST:
            # Keep first score - only update event count (keep original denormalized data)
            aux = {
                "selected_event_id": (existing_state.aux or {}).get("selected_event_id"),
                "event_count": event_count,
            }
            return await board_state_service.upsert_board_state(
                board_id=board.id,
                identity_id=identity_id,
                primary_value=existing_state.primary_value,
                aux=aux,
                player_name=existing_state.player_name,
                is_test=existing_state.is_test,
                timezone=existing_state.timezone,
                country=existing_state.country,
                city=existing_state.city,
                value_display=existing_state.value_display,
                metadata=existing_state.metadata,
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
                player_name=player_name,
                is_test=is_test,
                timezone=timezone,
                country=country,
                city=city,
                value_display=value_display,
                metadata=metadata,
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
                    player_name=player_name,
                    is_test=is_test,
                    timezone=timezone,
                    country=country,
                    city=city,
                    value_display=value_display,
                    metadata=metadata,
                )
            else:
                # Keep existing better score, just update event count (keep original data)
                aux = {
                    "selected_event_id": (existing_state.aux or {}).get("selected_event_id"),
                    "event_count": event_count,
                }
                return await board_state_service.upsert_board_state(
                    board_id=board.id,
                    identity_id=identity_id,
                    primary_value=existing_state.primary_value,
                    aux=aux,
                    player_name=existing_state.player_name,
                    is_test=existing_state.is_test,
                    timezone=existing_state.timezone,
                    country=existing_state.country,
                    city=existing_state.city,
                    value_display=existing_state.value_display,
                    metadata=existing_state.metadata,
                )

        # Fallback (shouldn't reach here with valid keep_strategy)
        return existing_state

    async def _handle_run_runs(
        self,
        board: Board,
        identity_id: IdentityID,
        event: ScoreEvent,
        value: float,
        player_name: str,
        is_test: bool,
        timezone: str | None,
        country: str | None,
        city: str | None,
        value_display: str | None,
        metadata: dict[str, Any] | None,
    ) -> RunEntry:
        """Handle RUN_RUNS board submission.

        Create a new run entry for each submission.

        Args:
            board: The board.
            identity_id: The identity.
            event: The created score event.
            value: The score value.
            player_name: Display name at submission time.
            is_test: Whether this is a test submission.
            timezone: Timezone from GeoIP.
            country: Country code from GeoIP.
            city: City name from GeoIP.
            value_display: Optional formatted display string.
            metadata: Optional custom metadata.

        Returns:
            Created RunEntry.
        """
        run_entry_service = RunEntryService(self.session)
        return await run_entry_service.create_run_entry(
            board_id=board.id,
            identity_id=identity_id,
            score_event_id=event.id,
            primary_value=value,
            player_name=player_name,
            is_test=is_test,
            timezone=timezone,
            country=country,
            city=city,
            value_display=value_display,
            metadata=metadata,
        )

    async def _handle_counter(
        self,
        board: Board,
        identity_id: IdentityID,
        event: ScoreEvent,
        delta: float,
        player_name: str,
        is_test: bool,
        timezone: str | None,
        country: str | None,
        city: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> BoardState:
        """Handle COUNTER board submission.

        Accumulate delta into board_state.

        Args:
            board: The board.
            identity_id: The identity.
            event: The created score event.
            delta: The delta value to accumulate.
            player_name: Display name at submission time.
            is_test: Whether this is a test submission.
            timezone: Timezone from GeoIP.
            country: Country code from GeoIP.
            city: City name from GeoIP.
            value_display: Optional formatted display string.
            metadata: Optional custom metadata.

        Returns:
            Updated BoardState.
        """
        board_state_service = BoardStateService(self.session)

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
                player_name=player_name,
                is_test=is_test,
                timezone=timezone,
                country=country,
                city=city,
                metadata=metadata,
            )

        # Accumulate delta
        current_value = existing_state.primary_value or 0.0
        new_value = current_value + delta
        event_count = (existing_state.aux or {}).get("event_count", 0) + 1

        aux = {
            "event_count": event_count,
            "last_event_id": str(event.id),
        }
        # For COUNTER boards, always update denormalized data with latest submission
        return await board_state_service.upsert_board_state(
            board_id=board.id,
            identity_id=identity_id,
            primary_value=new_value,
            aux=aux,
            player_name=player_name,
            is_test=is_test,
            timezone=timezone,
            country=country,
            city=city,
            metadata=metadata,
        )

    async def _update_submission_metadata(
        self,
        event: ScoreEvent,
        identity_id: IdentityID,
        board_id: BoardID,
        value: float | None,
    ) -> None:
        """Update submission metadata for future anti-cheat checks.

        Creates or updates the ScoreSubmissionMeta record for this identity/board
        combination to track submission patterns.

        Args:
            event: The created ScoreEvent.
            identity_id: The identity submitting.
            board_id: The board being submitted to.
            value: The score value (for duplicate detection).
        """
        meta_repo = ScoreSubmissionMetaRepository(self.session)
        existing_meta = await meta_repo.get_by_identity_and_board(identity_id, board_id)

        now = datetime.now(UTC)

        if existing_meta is None:
            # First submission - create new metadata
            meta = ScoreSubmissionMeta(
                score_event_id=event.id,
                identity_id=identity_id,
                board_id=board_id,
                submission_count=1,
                last_submission_at=now,
                last_score_value=value,
            )
            await meta_repo.create(meta)
        else:
            # Update existing metadata
            existing_meta.score_event_id = event.id
            existing_meta.submission_count += 1
            existing_meta.last_submission_at = now
            existing_meta.last_score_value = value
            await meta_repo.update(existing_meta)

    async def _create_score_flag(
        self,
        event: ScoreEvent,
        result: AntiCheatResult,
    ) -> ScoreFlag:
        """Create a score flag for admin review.

        Args:
            event: The flagged ScoreEvent.
            result: The anti-cheat result with flag details.

        Returns:
            The created ScoreFlag.
        """
        flag_repo = ScoreFlagRepository(self.session)

        flag = ScoreFlag(
            score_event_id=event.id,
            flag_type=result.flag_type,  # type: ignore[arg-type]
            confidence=result.confidence,  # type: ignore[arg-type]
            metadata=result.metadata or {},
        )
        return await flag_repo.create(flag)

    async def _schedule_ratio_updates(
        self,
        board_id: BoardID,
        identity_id: IdentityID,
        background_tasks: BackgroundTasks,
    ) -> None:
        """Schedule ratio board updates as background tasks.

        Checks if the updated board is a numerator or denominator for any ratio
        boards and schedules recomputation for each.

        Args:
            board_id: The board that was just updated.
            identity_id: The identity whose state was updated.
            background_tasks: FastAPI BackgroundTasks instance.
        """
        state_service = BoardStateService(self.session)
        dependent_configs = await state_service.find_dependent_ratio_boards(board_id)

        for config in dependent_configs:
            background_tasks.add_task(
                self._recompute_ratio_background,
                config,
                identity_id,
            )

    async def _recompute_ratio_background(
        self,
        config: BoardRatioConfig,
        identity_id: IdentityID,
    ) -> None:
        """Background task to recompute a ratio board state.

        Args:
            config: The ratio configuration.
            identity_id: The identity to recompute for.
        """
        state_service = BoardStateService(self.session)
        await state_service.recompute_ratio_for_identity(
            ratio_config=config,
            identity_id=identity_id,
        )

    # ==================== Query Methods (delegate to boards domain) ====================

    async def get_score_by_id(
        self,
        score_id: ScoreID,
        account_id: AccountID | None = None,
        game_id: GameID | None = None,
    ) -> tuple[BoardState | RunEntry, Board, int]:
        """Get a score by its ID with computed rank.

        The score_id uses scr_ prefix but internally maps to BoardState (bst_) or
        RunEntry (run_) based on board type. This method tries both services.

        Args:
            score_id: The score ID (scr_ prefix).
            account_id: Optional account ID for authorization check.
            game_id: Optional game ID for authorization check.

        Returns:
            Tuple of (BoardState or RunEntry, Board, rank) with the ranking data,
            board, and computed rank (1-indexed).

        Raises:
            EntityNotFoundError: If no matching BoardState or RunEntry is found.
        """
        # Extract UUID from ScoreID
        uuid = score_id.uuid

        board_state_service = BoardStateService(self.session)
        run_entry_service = RunEntryService(self.session)
        board_service = BoardService(self.session)

        # Try BoardStateService first
        board_state = await board_state_service.get_board_state(BoardStateID(uuid))
        if board_state is not None:
            board = await board_service.get_by_id_or_raise(board_state.board_id)
            # Compute rank using repository
            sort_fields = self._build_ranking_sort_fields(board)
            repo = BoardStateRepository(self.session)
            rank = await repo.get_rank(board_state, sort_fields)
            return board_state, board, rank

        # Try RunEntryService
        run_entry = await run_entry_service.get_run_entry(RunEntryID(uuid))
        if run_entry is not None:
            board = await board_service.get_by_id_or_raise(run_entry.board_id)
            # Compute rank using repository
            sort_fields = self._build_ranking_sort_fields(board)
            repo = RunEntryRepository(self.session)
            rank = await repo.get_rank(run_entry, sort_fields)
            return run_entry, board, rank

        raise EntityNotFoundError("Score", str(score_id))

    def _build_ranking_sort_fields(self, board: Board) -> list[SortField]:
        """Build sort fields for ranking based on board's sort direction.

        Args:
            board: The board entity.

        Returns:
            List of SortField objects for ranking queries.
        """
        value_direction = (
            SortDirection.ASC
            if board.sort_direction == BoardSortDirection.ASCENDING
            else SortDirection.DESC
        )
        return [
            SortField(name="primary_value", direction=value_direction),
            SortField(name="created_at", direction=SortDirection.DESC),
            SortField(name="id", direction=SortDirection.ASC),
        ]

    async def list_scores(
        self,
        board_id: BoardID,
        account_id: AccountID | None = None,
        game_id: GameID | None = None,
        identity_id: IdentityID | None = None,
        is_test: bool | None = None,
        *,
        pagination: PaginationParams,
        around_score_id: ScoreID | None = None,
        around_score_value: float | None = None,
    ) -> PaginatedResult[BoardState] | PaginatedResult[RunEntry]:
        """List scores for a board with optional filters and pagination.

        Delegates to BoardStateService or RunEntryService based on board type.

        Args:
            board_id: Board ID to list scores for.
            account_id: Optional account ID to filter by (for authorization).
            game_id: Optional game ID filter.
            identity_id: Optional identity ID filter.
            is_test: Optional filter for test scores.
            pagination: Pagination parameters.
            around_score_id: Optional score ID to center results around.
            around_score_value: Optional value to center results around.

        Returns:
            PaginatedResult containing BoardState or RunEntry objects.
        """
        board_service = BoardService(self.session)
        board = await board_service.get_by_id_or_raise(board_id)

        # Set sort spec based on board's sort direction
        if not pagination._user_provided_sort:
            value_direction = (
                SortDirection.ASC
                if board.sort_direction == BoardSortDirection.ASCENDING
                else SortDirection.DESC
            )
            pagination.sort_spec = [
                SortField(name="primary_value", direction=value_direction),
                SortField(name="created_at", direction=SortDirection.DESC),
                SortField(name="id", direction=SortDirection.ASC),
            ]
        else:
            # Translate public API field names to internal field names
            sort_field_aliases = {"value": "primary_value"}
            pagination.sort_spec = [
                SortField(
                    name=sort_field_aliases.get(field.name, field.name),
                    direction=field.direction,
                )
                for field in pagination.sort_spec
            ]

        # If around_score_id is provided, fetch the target entry first
        around_state: BoardState | None = None
        around_entry: RunEntry | None = None

        if around_score_id is not None:
            # Extract UUID from ScoreID and try to find the entry
            uuid = around_score_id.uuid

            if board.board_type == BoardType.RUN_RUNS:
                run_entry_service = RunEntryService(self.session)
                around_entry = await run_entry_service.get_run_entry(RunEntryID(uuid))
                if around_entry is None:
                    raise EntityNotFoundError("Score", str(around_score_id))
            else:
                board_state_service = BoardStateService(self.session)
                around_state = await board_state_service.get_board_state(BoardStateID(uuid))
                if around_state is None:
                    raise EntityNotFoundError("Score", str(around_score_id))

        # Delegate to appropriate service based on board type
        if board.board_type == BoardType.RUN_RUNS:
            run_entry_service = RunEntryService(self.session)
            return await run_entry_service.list_run_entries(
                board_id=board_id,
                identity_id=identity_id,
                is_test=is_test,
                pagination=pagination,
                around_entry=around_entry,
                around_value=around_score_value,
            )
        else:
            # RUN_IDENTITY, COUNTER, RATIO use BoardState
            board_state_service = BoardStateService(self.session)
            return await board_state_service.list_board_states(
                board_id=board_id,
                identity_id=identity_id,
                is_test=is_test,
                pagination=pagination,
                around_state=around_state,
                around_value=around_score_value,
            )

    async def check_player_name_availability(
        self,
        boards: list[tuple[BoardID, str, BoardType]],
        player_name: str,
        exclude_identity_id: IdentityID | None = None,
    ) -> tuple[str, bool, list[tuple[BoardID, str]]]:
        """Check if player name is available across multiple boards.

        Checks the appropriate table per board type:
        - RUN_RUNS → RunEntry table
        - RUN_IDENTITY/COUNTER → BoardState table

        Args:
            boards: List of (board_id, board_name, board_type) tuples to check.
            player_name: The player name to check.
            exclude_identity_id: Optional identity ID to exclude (same identity can reuse own name).

        Returns:
            Tuple of (normalised_name, is_available, conflicts_list)
            where conflicts_list contains (board_id, board_name) tuples.
        """
        normalised_name = _normalise_player_name(player_name)
        if not normalised_name:
            return normalised_name, True, []

        conflicts: list[tuple[BoardID, str]] = []

        for board_id, board_name, board_type in boards:
            # Select appropriate repository based on board type
            if board_type == BoardType.RUN_RUNS:
                repo = RunEntryRepository(self.session)
            else:  # RUN_IDENTITY, COUNTER
                repo = BoardStateRepository(self.session)

            is_available = await repo.is_player_name_available(
                board_id=board_id,
                player_name=normalised_name,
                exclude_identity_id=exclude_identity_id,
            )
            if not is_available:
                conflicts.append((board_id, board_name))

        return normalised_name, len(conflicts) == 0, conflicts
