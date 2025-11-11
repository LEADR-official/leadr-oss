"""Score service for managing score operations."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.boards.services.board_service import BoardService
from leadr.common.services import BaseService
from leadr.scores.domain.score import Score
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

    async def create_score(
        self,
        account_id: UUID,
        game_id: UUID,
        board_id: UUID,
        user_id: UUID,
        player_name: str,
        value: float,
        value_display: str | None = None,
        filter_timezone: str | None = None,
        filter_country: str | None = None,
        filter_city: str | None = None,
    ) -> Score:
        """Create a new score.

        Args:
            account_id: The ID of the account this score belongs to.
            game_id: The ID of the game this score belongs to.
            board_id: The ID of the board this score belongs to.
            user_id: The ID of the user who submitted this score.
            player_name: Display name of the player.
            value: Numeric value of the score for sorting/comparison.
            value_display: Optional formatted display string.
            filter_timezone: Optional timezone filter for categorization.
            filter_country: Optional country filter for categorization.
            filter_city: Optional city filter for categorization.

        Returns:
            The created Score domain entity.

        Raises:
            EntityNotFoundError: If the board doesn't exist.
            ValueError: If validation fails (board doesn't belong to account,
                       or game doesn't match board's game).

        Example:
            >>> score = await service.create_score(
            ...     account_id=account.id,
            ...     game_id=game.id,
            ...     board_id=board.id,
            ...     user_id=user.id,
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

        score = Score(
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            user_id=user_id,
            player_name=player_name,
            value=value,
            value_display=value_display,
            filter_timezone=filter_timezone,
            filter_country=filter_country,
            filter_city=filter_city,
        )

        return await self.repository.create(score)

    async def get_score(self, score_id: UUID) -> Score | None:
        """Get a score by its ID.

        Args:
            score_id: The ID of the score to retrieve.

        Returns:
            The Score domain entity if found, None otherwise.
        """
        return await self.get_by_id(score_id)

    async def list_scores(
        self,
        account_id: UUID,
        board_id: UUID | None = None,
        game_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> list[Score]:
        """List scores for an account with optional filters.

        Args:
            account_id: REQUIRED - Account ID to filter by (multi-tenant safety).
            board_id: Optional board ID to filter by.
            game_id: Optional game ID to filter by.
            user_id: Optional user ID to filter by.

        Returns:
            List of Score entities matching the filter criteria.
        """
        return await self.repository.filter(
            account_id=account_id,
            board_id=board_id,
            game_id=game_id,
            user_id=user_id,
        )

    async def update_score(
        self,
        score_id: UUID,
        player_name: str | None = None,
        value: float | None = None,
        value_display: str | None = None,
        filter_timezone: str | None = None,
        filter_country: str | None = None,
        filter_city: str | None = None,
    ) -> Score:
        """Update a score's mutable fields.

        Args:
            score_id: The ID of the score to update.
            player_name: Optional new player name.
            value: Optional new value.
            value_display: Optional new value display string.
            filter_timezone: Optional new timezone filter.
            filter_country: Optional new country filter.
            filter_city: Optional new city filter.

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
        if filter_timezone is not None:
            score.filter_timezone = filter_timezone
        if filter_country is not None:
            score.filter_country = filter_country
        if filter_city is not None:
            score.filter_city = filter_city

        return await self.repository.update(score)
