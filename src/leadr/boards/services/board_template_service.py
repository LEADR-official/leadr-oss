"""BoardTemplate service for managing board template operations."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.boards.domain.board_template import BoardTemplate
from leadr.boards.services.repositories import BoardTemplateRepository
from leadr.common.services import BaseService
from leadr.games.services.game_service import GameService


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

    async def create_board_template(
        self,
        account_id: UUID,
        game_id: UUID,
        name: str,
        repeat_interval: str,
        next_run_at: datetime,
        is_active: bool,
        name_template: str | None = None,
        config: dict[str, Any] | None = None,
        config_template: dict[str, Any] | None = None,
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
            config: Optional configuration object for boards created from this template.
            config_template: Optional template configuration for random generation.

        Returns:
            The created BoardTemplate domain entity.

        Raises:
            EntityNotFoundError: If the game doesn't exist.
            ValueError: If the game doesn't belong to the specified account.

        Example:
            >>> template = await service.create_board_template(
            ...     account_id=account.id,
            ...     game_id=game.id,
            ...     name="Weekly Speed Run Template",
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

        template = BoardTemplate(
            account_id=account_id,
            game_id=game_id,
            name=name,
            name_template=name_template,
            repeat_interval=repeat_interval,
            config=config or {},
            config_template=config_template or {},
            next_run_at=next_run_at,
            is_active=is_active,
        )

        return await self.repository.create(template)

    async def get_board_template(self, template_id: UUID) -> BoardTemplate | None:
        """Get a board template by its ID.

        Args:
            template_id: The ID of the template to retrieve.

        Returns:
            The BoardTemplate domain entity if found, None otherwise.
        """
        return await self.get_by_id(template_id)

    async def list_board_templates_by_account(self, account_id: UUID) -> list[BoardTemplate]:
        """List all board templates for an account.

        Args:
            account_id: The ID of the account to list templates for.

        Returns:
            List of BoardTemplate domain entities for the account.
        """
        return await self.repository.filter(account_id)

    async def list_board_templates_by_game(
        self, account_id: UUID, game_id: UUID
    ) -> list[BoardTemplate]:
        """List all board templates for a specific game.

        Args:
            account_id: The ID of the account (for multi-tenant safety).
            game_id: The ID of the game to list templates for.

        Returns:
            List of BoardTemplate domain entities for the game.
        """
        return await self.repository.filter(account_id, game_id=game_id)

    async def update_board_template(
        self,
        template_id: UUID,
        name: str | None = None,
        name_template: str | None = None,
        repeat_interval: str | None = None,
        config: dict[str, Any] | None = None,
        config_template: dict[str, Any] | None = None,
        next_run_at: datetime | None = None,
        is_active: bool | None = None,
    ) -> BoardTemplate:
        """Update board template fields.

        Args:
            template_id: The ID of the template to update.
            name: New template name, if provided.
            name_template: New name template, if provided.
            repeat_interval: New repeat interval, if provided.
            config: New config, if provided.
            config_template: New config template, if provided.
            next_run_at: New next_run_at, if provided.
            is_active: New is_active status, if provided.

        Returns:
            The updated BoardTemplate domain entity.

        Raises:
            EntityNotFoundError: If the template doesn't exist.
        """
        template = await self.get_by_id_or_raise(template_id)

        if name is not None:
            template.name = name
        if name_template is not None:
            template.name_template = name_template
        if repeat_interval is not None:
            template.repeat_interval = repeat_interval
        if config is not None:
            template.config = config
        if config_template is not None:
            template.config_template = config_template
        if next_run_at is not None:
            template.next_run_at = next_run_at
        if is_active is not None:
            template.is_active = is_active

        return await self.repository.update(template)
