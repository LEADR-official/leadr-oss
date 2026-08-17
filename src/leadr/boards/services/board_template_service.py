"""BoardTemplate service for managing board template operations."""

import re
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.boards.domain.board import BoardType, KeepStrategy, SortDirection
from leadr.boards.domain.board_template import BoardTemplate
from leadr.boards.domain.interval_parser import parse_interval
from leadr.boards.services.repositories import BoardTemplateRepository
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import AccountID, BoardTemplateID, GameID
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.common.services import BaseService
from leadr.games.services.game_service import GameService
from leadr.logging import get_logger

logger = get_logger(__name__)


class BoardTemplateService(BaseService[BoardTemplate, BoardTemplateRepository]):
    """Service for managing board template lifecycle and operations.

    This service orchestrates board template creation, updates, and retrieval
    by coordinating between the domain models and repository layer.
    Ensures business rules like game validation are enforced.
    """

    def _create_repository(self, session: AsyncSession) -> BoardTemplateRepository:
        """Create BoardTemplateRepository instance."""
        return BoardTemplateRepository(session)

    def _get_entity_name(self) -> str:
        """Get entity name for error messages."""
        return "BoardTemplate"

    @staticmethod
    def _validate_name_template(name_template: str | None) -> None:
        """Validate name_template contains only valid placeholders.

        Args:
            name_template: The name template string to validate.

        Raises:
            ValueError: If the name_template contains invalid placeholders.
        """
        if name_template is None:
            return

        # Define valid placeholders
        valid_placeholders = {
            "year",
            "month",
            "month_short",
            "week",
            "quarter",
            "date",
            "series",
        }

        # Extract all placeholders from the template
        placeholder_pattern = r"\{(\w+)\}"
        found_placeholders = set(re.findall(placeholder_pattern, name_template))

        # Check for invalid placeholders
        invalid_placeholders = found_placeholders - valid_placeholders
        if invalid_placeholders:
            invalid_str = ", ".join(sorted(invalid_placeholders))
            valid_str = ", ".join(sorted(valid_placeholders))
            raise ValueError(
                f"Invalid placeholder(s) in name_template: {invalid_str}. "
                f"Valid placeholders are: {valid_str}"
            )

    async def create_board_template(
        self,
        account_id: AccountID,
        game_id: GameID,
        name: str,
        slug: str | None,
        repeat_interval: str,
        next_run_at: datetime,
        is_active: bool,
        is_published: bool = True,
        unique_player_names: bool = False,
        name_template: str | None = None,
        series: str | None = None,
        icon: str | None = "fa-crown",
        unit: str | None = None,
        sort_direction: SortDirection = SortDirection.DESCENDING,
        board_type: BoardType = BoardType.RUN_IDENTITY,
        keep_strategy: KeepStrategy = KeepStrategy.BEST,
        starts_at: datetime | None = None,
        ends_at: datetime | None = None,
        tags: list[str] | None = None,
        config: dict[str, Any] | None = None,
    ) -> BoardTemplate:
        """Create a new board template.

        Args:
            account_id: The ID of the account that owns this template.
            game_id: The ID of the game this template belongs to.
            name: The template name.
            repeat_interval: PostgreSQL interval syntax for repeat frequency.
            next_run_at: Next scheduled time to create a board.
            is_active: Whether the template is currently active.
            name_template: Optional template string for generating board names.
            series: Optional series identifier for sequential board naming.
            config: Optional configuration object for boards created from this template.
            config_template: Optional template configuration for random generation.

        Returns:
            The created BoardTemplate domain entity.

        Raises:
            EntityNotFoundError: If the game doesn't exist.
            ValueError: If the game doesn't belong to the specified account or
                       if name_template contains invalid placeholders.

        Example:
            >>> template = await service.create_board_template(
            ...     account_id=account.id,
            ...     game_id=game.id,
            ...     name="Weekly Speed Run Template",
            ...     name_template="Week {series} - {year}",
            ...     series="weekly",
            ...     repeat_interval="7 days",
            ...     next_run_at=datetime.now(UTC) + timedelta(days=7),
            ...     is_active=True,
            ... )
        """
        # Validate that game exists and belongs to account
        game_service = GameService(self.repository.session)
        game = await game_service.get_by_id_or_raise(game_id)

        if game.account_id != account_id:
            raise ValueError(f"Game {game_id} does not belong to account {account_id}")

        # Validate name_template placeholders
        self._validate_name_template(name_template)

        template = BoardTemplate(
            account_id=account_id,
            game_id=game_id,
            name=name,
            slug=slug,
            name_template=name_template,
            series=series,
            icon=icon,
            unit=unit,
            sort_direction=sort_direction,
            board_type=board_type,
            keep_strategy=keep_strategy,
            starts_at=starts_at,
            ends_at=ends_at,
            tags=tags or [],
            repeat_interval=repeat_interval,
            config=config or {},
            next_run_at=next_run_at,
            is_active=is_active,
            is_published=is_published,
            unique_player_names=unique_player_names,
        )

        created_template = await self.repository.create(template)
        logger.info(
            "Board template created", template_id=str(created_template.id), game_id=str(game_id)
        )
        return created_template

    async def get_board_template(self, template_id: BoardTemplateID) -> BoardTemplate | None:
        """Get a board template by its ID.

        Args:
            template_id: The ID of the template to retrieve.

        Returns:
            The BoardTemplate domain entity if found, None otherwise.
        """
        return await self.get_by_id(template_id)

    async def list_board_templates_by_account(
        self,
        account_id: AccountID | None,
        *,
        pagination: PaginationParams,
    ) -> PaginatedResult[BoardTemplate]:
        """List all board templates for an account with pagination.

        Args:
            account_id: The ID of the account to list templates for. If None, returns all
                templates (superadmin use case).
            pagination: Pagination parameters (required).

        Returns:
            PaginatedResult containing BoardTemplate entities matching the filter criteria.
        """
        return await self.repository.filter(account_id, pagination=pagination)

    async def list_board_templates_by_game(
        self,
        account_id: AccountID | None,
        game_id: GameID,
        *,
        pagination: PaginationParams,
    ) -> PaginatedResult[BoardTemplate]:
        """List all board templates for a specific game with pagination.

        Args:
            account_id: The ID of the account. If None, returns templates from all accounts
                (superadmin use case).
            game_id: The ID of the game to list templates for.
            pagination: Pagination parameters (required).

        Returns:
            PaginatedResult containing BoardTemplate entities matching the filter criteria.
        """
        return await self.repository.filter(account_id, game_id=game_id, pagination=pagination)

    async def update_board_template(
        self, template_id: BoardTemplateID, **updates: Any
    ) -> BoardTemplate:
        """Update board template fields.

        Accepts any fields to update as keyword arguments. Only fields
        explicitly provided will be updated, allowing null values to
        clear optional fields.

        Args:
            template_id: The ID of the template to update.
            **updates: Field names and values to update

        Returns:
            The updated BoardTemplate domain entity.

        Raises:
            EntityNotFoundError: If the template doesn't exist.
            ValueError: If name_template contains invalid placeholders.
        """
        template = await self.get_by_id_or_raise(template_id)

        # Validate name_template if provided
        if "name_template" in updates:
            self._validate_name_template(updates["name_template"])

        # Apply all updates atomically - validation runs once at the end
        template = template.model_copy(update=updates)

        return await self.repository.update(template)

    async def advance_template_schedule(self, template_id: BoardTemplateID) -> BoardTemplate:
        """Advance a template's next_run_at by its repeat_interval.

        This is typically called after successfully creating a board from the template.

        Args:
            template_id: The ID of the template to advance.

        Returns:
            The updated BoardTemplate with advanced next_run_at.

        Raises:
            EntityNotFoundError: If the template doesn't exist.
            ValueError: If the repeat_interval cannot be parsed.

        Example:
            >>> template = await service.advance_template_schedule(template.id)
            >>> # template.next_run_at is now advanced by repeat_interval
        """
        template = await self.get_by_id_or_raise(template_id)

        # Parse interval and add to current next_run_at
        duration = parse_interval(template.repeat_interval)
        template.next_run_at = template.next_run_at + duration

        return await self.repository.update(template)
