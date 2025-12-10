"""Score service for managing score operations."""

from datetime import UTC, datetime
from typing import Any, overload

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.boards.domain.board import KeepStrategy, SortDirection
from leadr.boards.services.board_service import BoardService
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import AccountID, BoardID, DeviceID, GameID, ScoreID
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.common.services import BaseService
from leadr.games.services.game_service import GameService
from leadr.scores.domain.anti_cheat.enums import FlagAction, TrustTier
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
        scores = await self.repository.filter(
            account_id=account_id,
            board_id=board_id,
            device_id=device_id,
        )
        return scores[0] if scores else None

    def _is_better_score(
        self, new_value: float, existing_value: float, sort_direction: SortDirection
    ) -> bool:
        """Determine if new score is better than existing based on sort direction.

        Args:
            new_value: The value of the new score.
            existing_value: The value of the existing score.
            sort_direction: The sort direction of the board.

        Returns:
            True if new score is better (should replace existing), False otherwise.
        """
        if sort_direction == SortDirection.ASCENDING:
            # Lower is better for ascending (e.g., race times)
            return new_value < existing_value
        else:  # DESCENDING
            # Higher is better for descending (e.g., points/kills)
            return new_value > existing_value

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
                # Return existing first score, don't create new one
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
                    # New score is worse or equal, return existing better score
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

        # Save score to database
        saved_score = await self.repository.create(score)

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

    @overload
    async def list_scores(
        self,
        account_id: AccountID | None,
        board_id: BoardID | None = None,
        game_id: GameID | None = None,
        device_id: DeviceID | None = None,
        pagination: None = None,
    ) -> list[Score]: ...

    @overload
    async def list_scores(
        self,
        account_id: AccountID | None,
        board_id: BoardID | None = None,
        game_id: GameID | None = None,
        device_id: DeviceID | None = None,
        pagination: PaginationParams = ...,
    ) -> PaginatedResult[Score]: ...

    async def list_scores(
        self,
        account_id: AccountID | None,
        board_id: BoardID | None = None,
        game_id: GameID | None = None,
        device_id: DeviceID | None = None,
        pagination: PaginationParams | None = None,
    ) -> list[Score] | PaginatedResult[Score]:
        """List scores for an account with optional filters and pagination.

        Args:
            account_id: Account ID to filter by. If None, returns all scores
                (superadmin use case).
            board_id: Optional board ID to filter by.
            game_id: Optional game ID to filter by.
            device_id: Optional device ID to filter by.
            pagination: Optional pagination parameters.

        Returns:
            List of Score entities if no pagination, PaginatedResult if pagination provided.
        """
        return await self.repository.filter(
            account_id=account_id,
            board_id=board_id,
            game_id=game_id,
            device_id=device_id,
            pagination=pagination,
        )

    async def update_score(
        self,
        score_id: ScoreID,
        player_name: str | None = None,
        value: float | None = None,
        value_display: str | None = None,
        timezone: str | None = None,
        country: str | None = None,
        city: str | None = None,
        metadata: Any | None = None,
    ) -> Score:
        """Update a score's mutable fields.

        Args:
            score_id: The ID of the score to update.
            player_name: Optional new player name.
            value: Optional new value.
            value_display: Optional new value display string.
            timezone: Optional new timezone.
            country: Optional new country.
            city: Optional new city.
            metadata: Optional new metadata.

        Returns:
            The updated Score entity.

        Raises:
            EntityNotFoundError: If the score doesn't exist.
        """
        score = await self.get_by_id_or_raise(score_id)

        if player_name is not None:
            score.player_name = player_name
        if value is not None:
            score.value = value
        if value_display is not None:
            score.value_display = value_display
        if timezone is not None:
            score.timezone = timezone
        if country is not None:
            score.country = country
        if city is not None:
            score.city = city
        if metadata is not None:
            score.metadata = metadata

        return await self.repository.update(score)
