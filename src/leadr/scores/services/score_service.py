"""Score service for managing score operations."""

from datetime import UTC, datetime
from typing import Any

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.boards.domain.board import KeepStrategy
from leadr.boards.domain.board import SortDirection as BoardSortDirection
from leadr.boards.services.board_service import BoardService
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import AccountID, BoardID, DeviceID, GameID, ScoreID
from leadr.common.domain.pagination import SortDirection, SortField
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.common.services import BaseService
from leadr.games.services.game_service import GameService
from leadr.scores.domain.anti_cheat.enums import FlagAction, ScoreStatus, TrustTier
from leadr.scores.domain.anti_cheat.models import AntiCheatResult, ScoreFlag, ScoreSubmissionMeta
from leadr.scores.domain.score import Score
from leadr.scores.services.anti_cheat_repositories import (
    ScoreFlagRepository,
    ScoreSubmissionMetaRepository,
)
from leadr.scores.services.anti_cheat_service import AntiCheatService
from leadr.scores.services.repositories import ScoreRepository


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
        if board.keep_strategy == KeepStrategy.FIRST_ONLY:
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
        elif board.keep_strategy == KeepStrategy.LATEST_ONLY:
            existing_score = await self._get_active_score_for_device(
                account_id=account_id,
                device_id=device_id,
                board_id=board_id,
            )
            if existing_score is not None:
                # Soft-delete the old score before creating new one
                await self.soft_delete(existing_score.id)
        elif board.keep_strategy == KeepStrategy.BEST_ONLY:
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

        # Anti-cheat checking (if enabled and device_id provided)
        anti_cheat_result = None
        if device_id is not None:
            # Fetch game to check if anti-cheat is enabled
            game_service = GameService(self.repository.session)
            game = await game_service.get_by_id_or_raise(game_id)

            if game.anti_cheat_enabled:
                # Run anti-cheat checks
                anti_cheat_service = AntiCheatService(self.repository.session)
                anti_cheat_result = await anti_cheat_service.check_submission(
                    score=score,
                    trust_tier=trust_tier,
                    device_id=device_id,
                    board_id=board_id,
                )

                # If rejected, don't create the score
                if anti_cheat_result.action == FlagAction.REJECT:
                    raise ValueError(
                        f"Score submission rejected by anti-cheat: {anti_cheat_result.reason}"
                    )

                # Set status based on anti-cheat result
                if anti_cheat_result.action == FlagAction.FLAG:
                    score.flag_for_review()  # status = UNDER_REVIEW
                else:
                    score.activate()  # status = ACTIVE
            else:
                # No anti-cheat - activate immediately
                score.activate()
        else:
            # No device_id (shouldn't happen in practice) - activate
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

        This method is designed to be called as a background task after score creation
        to avoid blocking the HTTP response.

        Args:
            saved_score: The score that was created
            device_id: ID of the device that submitted the score
            board_id: ID of the board the score was submitted to
            anti_cheat_result: Result from anti-cheat check (or None)
        """
        if anti_cheat_result is None:
            return

        meta_repo = ScoreSubmissionMetaRepository(self.repository.session)
        now = datetime.now(UTC)

        # Get or create submission metadata
        meta = await meta_repo.get_by_device_and_board(device_id, board_id)

        if meta is None:
            # Create new metadata
            meta = ScoreSubmissionMeta(
                score_id=saved_score.id,
                device_id=device_id,
                board_id=board_id,
                submission_count=1,
                last_submission_at=now,
                last_score_value=saved_score.value,
            )
            await meta_repo.create(meta)
        else:
            # Update existing metadata
            meta.score_id = saved_score.id
            meta.submission_count += 1
            meta.last_submission_at = now
            meta.last_score_value = saved_score.value
            await meta_repo.update(meta)

        # Create flag if score was flagged
        if anti_cheat_result.action == FlagAction.FLAG:
            from leadr.scores.domain.anti_cheat.enums import ScoreFlagStatus

            flag_repo = ScoreFlagRepository(self.repository.session)
            flag = ScoreFlag(
                score_id=saved_score.id,
                flag_type=anti_cheat_result.flag_type,  # type: ignore[arg-type]
                confidence=anti_cheat_result.confidence,  # type: ignore[arg-type]
                metadata=anti_cheat_result.metadata or {},
                status=ScoreFlagStatus.PENDING,
            )
            await flag_repo.create(flag)

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
