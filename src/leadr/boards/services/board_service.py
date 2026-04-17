"""Board service for managing board operations."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.boards.domain.board import Board, BoardType, KeepStrategy, SortDirection
from leadr.boards.domain.interval_parser import parse_interval
from leadr.boards.services.repositories import BoardRepository
from leadr.boards.services.short_code_generator import generate_unique_short_code
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import AccountID, BoardID, BoardTemplateID, GameID
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.common.services import BaseService
from leadr.common.utils.slug import generate_unique_slug_with_retry
from leadr.games.services.game_service import GameService
from leadr.logging import get_logger

if TYPE_CHECKING:
    from leadr.boards.domain.board_template import BoardTemplate

logger = get_logger(__name__)


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
        account_id: AccountID,
        game_id: GameID,
        name: str,
        icon: str | None = "fa-crown",
        unit: str | None = None,
        is_active: bool = True,
        is_published: bool = True,
        sort_direction: SortDirection = SortDirection.DESCENDING,
        board_type: BoardType = BoardType.RUN_IDENTITY,
        keep_strategy: KeepStrategy = KeepStrategy.BEST,
        slug: str | None = None,
        short_code: str | None = None,
        created_from_template_id: BoardTemplateID | None = None,
        template_name: str | None = None,
        starts_at: datetime | None = None,
        ends_at: datetime | None = None,
        tags: list[str] | None = None,
        description: str | None = None,
    ) -> Board:
        """Create a new board.

        Args:
            account_id: The ID of the account that owns this board.
            game_id: The ID of the game this board belongs to.
            name: The board name.
            icon: Icon identifier for the board. Defaults to "fa-crown".
            unit: Unit of measurement for scores. Defaults to None.
            is_active: Whether the board is currently active. Defaults to True.
            is_published: Whether the board is published and visible on public web views.
                Defaults to True.
            sort_direction: Direction to sort scores. Defaults to DESCENDING.
            keep_strategy: Strategy for keeping multiple scores from same user. Defaults to ALL.
            slug: Optional URL-friendly slug. If not provided, auto-generated from name.
            short_code: Globally unique short code for direct sharing.
            created_from_template_id: Optional template ID this board was created from.
            template_name: Optional template name.
            starts_at: Optional start time for time-bounded boards.
            ends_at: Optional end time for time-bounded boards.
            tags: Optional list of tags for categorization.
            description: Optional short description of the board.

        Returns:
            The created Board domain entity.

        Raises:
            EntityNotFoundError: If the game doesn't exist.
            ValueError: If the game doesn't belong to the specified account or slug is invalid.

        Example:
            >>> board = await service.create_board(
            ...     account_id=account.id,
            ...     game_id=game.id,
            ...     name="Speed Run Board",
            ...     icon="trophy",
            ...     unit="seconds",
            ...     is_active=True,
            ...     sort_direction=SortDirection.ASCENDING,
            ...     keep_strategy=KeepStrategy.BEST,
            ... )
        """
        # Validate that game exists and belongs to account
        game_service = GameService(self.repository.session)
        game = await game_service.get_by_id_or_raise(game_id)

        if game.account_id != account_id:
            raise ValueError(f"Game {game_id} does not belong to account {account_id}")

        # Generate unique short code if not provided
        if short_code is None:
            short_code = await generate_unique_short_code(self.repository.session)

        # Generate or validate slug
        if slug is None:
            # Auto-generate unique slug from name with collision handling
            async def check_slug_exists(slug_to_check: str) -> bool:
                """Check if slug exists for this account/game combination."""
                pagination = PaginationParams(cursor=None, limit=1, sort=None)
                result = await self.repository.filter(
                    account_id=account_id,
                    game_id=game_id,
                    slug=slug_to_check,
                    is_active=True,
                    pagination=pagination,
                )
                return len(result.items) > 0

            slug = await generate_unique_slug_with_retry(
                base_text=name,
                check_exists=check_slug_exists,
                max_retries=10,
            )
        else:
            # Use provided slug - validation will happen in Board domain model
            # Check for uniqueness constraint violation (active board with same slug)
            pagination = PaginationParams(cursor=None, limit=1, sort=None)
            result = await self.repository.filter(
                account_id=account_id,
                game_id=game_id,
                slug=slug,
                is_active=True,
                pagination=pagination,
            )
            if len(result.items) > 0:
                raise ValueError(f"An active board with slug '{slug}' already exists for this game")

        board = Board(
            account_id=account_id,
            game_id=game_id,
            name=name,
            slug=slug,
            icon=icon,
            short_code=short_code,
            unit=unit,
            is_active=is_active,
            is_published=is_published,
            sort_direction=sort_direction,
            board_type=board_type,
            keep_strategy=keep_strategy,
            created_from_template_id=created_from_template_id,
            template_name=template_name,
            starts_at=starts_at,
            ends_at=ends_at,
            tags=tags or [],
            description=description,
        )

        created_board = await self.repository.create(board)
        logger.info("Board created", board_id=str(created_board.id), game_id=str(game_id))
        return created_board

    async def create_board_from_template(self, template: "BoardTemplate") -> Board:
        """Create a new board from a board template.

        Extracts configuration from the template and calculates time boundaries
        based on the template's repeat_interval. Automatically generates a unique
        short code for the board. If the template has a series field, generates
        a sequential series value and uses it in the board name.

        Args:
            template: The BoardTemplate to create a board from.

        Returns:
            The created Board domain entity.

        Raises:
            ValueError: If interval parsing fails, game doesn't belong to account,
                       or name generation fails.

        Example:
            >>> board = await service.create_board_from_template(template)
        """
        # Get current timestamp for name generation
        now = datetime.now(UTC)

        # Calculate series value if name_template uses {series} placeholder
        series_value = None
        if template.name_template and "{series}" in template.name_template:
            # Count existing boards from this template and increment
            count = await self.repository.count_boards_by_template(template.id)
            series_value = count + 1

        # Generate board name using template
        board_name = template.generate_name(timestamp=now, series_value=series_value)

        # Parse interval to calculate time boundaries
        # Use template boundaries if set, otherwise derive from interval
        duration = parse_interval(template.repeat_interval)
        starts_at = template.starts_at if template.starts_at else template.next_run_at
        ends_at = template.ends_at if template.ends_at else (starts_at + duration)

        # Use first-class fields from template
        # Create board using standard creation method (short_code generated automatically)
        return await self.create_board(
            account_id=template.account_id,
            game_id=template.game_id,
            name=board_name,
            slug=template.slug,  # Use template slug if set, otherwise auto-generate
            icon=template.icon,
            unit=template.unit,
            is_active=True,  # New boards from templates are always active
            is_published=template.is_published,
            sort_direction=template.sort_direction,
            board_type=template.board_type,
            keep_strategy=template.keep_strategy,
            created_from_template_id=template.id,
            template_name=template.name,
            starts_at=starts_at,
            ends_at=ends_at,
            tags=template.tags,
        )

    async def get_board(self, board_id: BoardID) -> Board | None:
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

    async def list_boards_by_account(self, account_id: AccountID) -> list[Board]:
        """List all boards for an account.

        Args:
            account_id: The ID of the account to list boards for.

        Returns:
            List of Board domain entities for the account.
        """
        pagination = PaginationParams(cursor=None, limit=1000, sort=None)
        result = await self.repository.filter(account_id=account_id, pagination=pagination)
        return list(result.items)

    async def list_boards(
        self,
        account_id: AccountID | None = None,
        game_id: GameID | None = None,
        code: str | None = None,
        slug: str | None = None,
        is_active: bool | None = None,
        is_published: bool | None = None,
        starts_before: datetime | None = None,
        starts_after: datetime | None = None,
        ends_before: datetime | None = None,
        ends_after: datetime | None = None,
        *,
        pagination: PaginationParams,
    ) -> PaginatedResult[Board]:
        """List boards with optional filtering and pagination.

        Args:
            account_id: Optional account ID to filter by
            game_id: Optional game ID to filter by
            code: Optional short code to filter by
            slug: Optional slug to filter by
            is_active: Optional filter for active status
            is_published: Optional filter for published status
            starts_before: Optional filter for boards starting before this time
            starts_after: Optional filter for boards starting after this time
            ends_before: Optional filter for boards ending before this time
            ends_after: Optional filter for boards ending after this time
            pagination: Pagination parameters (required)

        Returns:
            PaginatedResult containing Board entities matching the filter criteria.
        """
        return await self.repository.filter(
            account_id=account_id,
            game_id=game_id,
            code=code,
            slug=slug,
            is_active=is_active,
            is_published=is_published,
            starts_before=starts_before,
            starts_after=starts_after,
            ends_before=ends_before,
            ends_after=ends_after,
            pagination=pagination,
        )

    async def update_board(self, board_id: BoardID, **updates: Any) -> Board:
        """Update board fields.

        Accepts any fields to update as keyword arguments. Only fields
        explicitly provided will be updated, allowing null values to
        clear optional fields.

        Args:
            board_id: The ID of the board to update
            **updates: Field names and values to update

        Returns:
            The updated Board domain entity

        Raises:
            EntityNotFoundError: If the board doesn't exist
        """
        board = await self.get_by_id_or_raise(board_id)

        # Apply all updates atomically - validation runs once at the end
        # This prevents validation errors when updating cross-dependent fields
        # like board_type and keep_strategy together
        board = board.model_copy(update=updates)

        return await self.repository.update(board)
