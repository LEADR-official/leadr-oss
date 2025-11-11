"""Board service for managing board operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.boards.domain.board import Board, KeepStrategy, SortDirection
from leadr.boards.services.repositories import BoardRepository
from leadr.common.services import BaseService
from leadr.games.services.game_service import GameService


class BoardService(BaseService[Board, BoardRepository]):
    """Service for managing board lifecycle and operations.

    This service orchestrates board creation, updates, and retrieval
    by coordinating between the domain models and repository layer.
    Ensures business rules like game validation are enforced.
    """

    def _create_repository(self, session: AsyncSession) -> BoardRepository:
        """Create BoardRepository instance."""
        return BoardRepository(session)

    def _get_entity_name(self) -> str:
        """Get entity name for error messages."""
        return "Board"

    async def create_board(
        self,
        account_id: UUID,
        game_id: UUID,
        name: str,
        icon: str,
        short_code: str,
        unit: str,
        is_active: bool,
        sort_direction: SortDirection,
        keep_strategy: KeepStrategy,
        template_id: UUID | None = None,
        template_name: str | None = None,
        starts_at: datetime | None = None,
        ends_at: datetime | None = None,
        tags: list[str] | None = None,
    ) -> Board:
        """Create a new board.

        Args:
            account_id: The ID of the account that owns this board.
            game_id: The ID of the game this board belongs to.
            name: The board name.
            icon: Icon identifier for the board.
            short_code: Globally unique short code for direct sharing.
            unit: Unit of measurement for scores.
            is_active: Whether the board is currently active.
            sort_direction: Direction to sort scores.
            keep_strategy: Strategy for keeping multiple scores from same user.
            template_id: Optional template ID this board was created from.
            template_name: Optional template name.
            starts_at: Optional start time for time-bounded boards.
            ends_at: Optional end time for time-bounded boards.
            tags: Optional list of tags for categorization.

        Returns:
            The created Board domain entity.

        Raises:
            EntityNotFoundError: If the game doesn't exist.
            ValueError: If the game doesn't belong to the specified account.

        Example:
            >>> board = await service.create_board(
            ...     account_id=account.id,
            ...     game_id=game.id,
            ...     name="Speed Run Board",
            ...     icon="trophy",
            ...     short_code="SR2025",
            ...     unit="seconds",
            ...     is_active=True,
            ...     sort_direction=SortDirection.ASCENDING,
            ...     keep_strategy=KeepStrategy.BEST_ONLY,
            ... )
        """
        # Validate that game exists and belongs to account
        game_service = GameService(self.repository.session)
        game = await game_service.get_by_id_or_raise(game_id)

        if game.account_id != account_id:
            raise ValueError(f"Game {game_id} does not belong to account {account_id}")

        board = Board(
            account_id=account_id,
            game_id=game_id,
            name=name,
            icon=icon,
            short_code=short_code,
            unit=unit,
            is_active=is_active,
            sort_direction=sort_direction,
            keep_strategy=keep_strategy,
            template_id=template_id,
            template_name=template_name,
            starts_at=starts_at,
            ends_at=ends_at,
            tags=tags or [],
        )

        return await self.repository.create(board)

    async def get_board(self, board_id: UUID) -> Board | None:
        """Get a board by its ID.

        Args:
            board_id: The ID of the board to retrieve.

        Returns:
            The Board domain entity if found, None otherwise.
        """
        return await self.get_by_id(board_id)

    async def get_board_by_short_code(self, short_code: str) -> Board | None:
        """Get a board by its short_code.

        Args:
            short_code: The short_code to search for.

        Returns:
            The Board domain entity if found, None otherwise.
        """
        return await self.repository.get_by_short_code(short_code)

    async def list_boards_by_account(self, account_id: UUID) -> list[Board]:
        """List all boards for an account.

        Args:
            account_id: The ID of the account to list boards for.

        Returns:
            List of Board domain entities for the account.
        """
        return await self.repository.filter(account_id)

    async def update_board(
        self,
        board_id: UUID,
        name: str | None = None,
        icon: str | None = None,
        short_code: str | None = None,
        unit: str | None = None,
        is_active: bool | None = None,
        sort_direction: SortDirection | None = None,
        keep_strategy: KeepStrategy | None = None,
        template_id: UUID | None = None,
        template_name: str | None = None,
        starts_at: datetime | None = None,
        ends_at: datetime | None = None,
        tags: list[str] | None = None,
    ) -> Board:
        """Update board fields.

        Args:
            board_id: The ID of the board to update
            name: New board name, if provided
            icon: New icon, if provided
            short_code: New short_code, if provided
            unit: New unit, if provided
            is_active: New is_active status, if provided
            sort_direction: New sort_direction, if provided
            keep_strategy: New keep_strategy, if provided
            template_id: New template_id, if provided
            template_name: New template_name, if provided
            starts_at: New starts_at, if provided
            ends_at: New ends_at, if provided
            tags: New tags list, if provided

        Returns:
            The updated Board domain entity

        Raises:
            EntityNotFoundError: If the board doesn't exist
        """
        board = await self.get_by_id_or_raise(board_id)

        if name is not None:
            board.name = name
        if icon is not None:
            board.icon = icon
        if short_code is not None:
            board.short_code = short_code
        if unit is not None:
            board.unit = unit
        if is_active is not None:
            board.is_active = is_active
        if sort_direction is not None:
            board.sort_direction = sort_direction
        if keep_strategy is not None:
            board.keep_strategy = keep_strategy
        if template_id is not None:
            board.template_id = template_id
        if template_name is not None:
            board.template_name = template_name
        if starts_at is not None:
            board.starts_at = starts_at
        if ends_at is not None:
            board.ends_at = ends_at
        if tags is not None:
            board.tags = tags

        return await self.repository.update(board)
