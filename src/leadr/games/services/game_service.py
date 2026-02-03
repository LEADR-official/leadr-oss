"""Game service for managing game operations."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.ids import AccountID, BoardID, GameID
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.common.services import BaseService
from leadr.common.utils.slug import generate_unique_slug_with_retry
from leadr.games.domain.game import Game
from leadr.games.services.repositories import GameRepository
from leadr.logging import get_logger

logger = get_logger(__name__)


class GameService(BaseService[Game, GameRepository]):
    """Service for managing game lifecycle and operations.

    This service orchestrates game creation, updates, and retrieval
    by coordinating between the domain models and repository layer.
    """

    def _create_repository(self, session: AsyncSession) -> GameRepository:
        """Create GameRepository instance."""
        return GameRepository(session)

    def _get_entity_name(self) -> str:
        """Get entity name for error messages."""
        return "Game"

    async def create_game(
        self,
        account_id: AccountID,
        name: str,
        slug: str | None = None,
        steam_app_id: str | None = None,
        default_board_id: BoardID | None = None,
        anti_cheat_enabled: bool = True,
        description: str | None = None,
        tags: list[str] | None = None,
        page_url: str | None = None,
    ) -> Game:
        """Create a new game.

        Args:
            account_id: The ID of the account that owns this game.
            name: The game name.
            slug: Optional URL-friendly slug. If not provided, auto-generated from name.
            steam_app_id: Optional Steam application ID.
            default_board_id: Optional default leaderboard ID.
            anti_cheat_enabled: Whether anti-cheat is enabled (defaults to True).
            description: Optional short description of the game.
            tags: Optional list of tags for categorizing the game.
            page_url: Optional URL to the game's page or website.

        Returns:
            The created Game domain entity.

        Raises:
            ValueError: If slug is invalid or already exists globally.

        Example:
            >>> game = await service.create_game(
            ...     account_id=account.id,
            ...     name="Super Awesome Game",
            ...     steam_app_id="123456",
            ... )
        """
        # Generate or validate slug
        if slug is None:
            # Auto-generate unique slug from name with collision handling
            async def check_slug_exists(slug_to_check: str) -> bool:
                """Check if slug exists globally."""
                existing = await self.repository.get_by_slug(slug_to_check)
                return existing is not None

            slug = await generate_unique_slug_with_retry(
                base_text=name,
                check_exists=check_slug_exists,
                max_retries=10,
            )
        else:
            # Use provided slug - validation will happen in Game domain model
            # Check for global uniqueness constraint violation
            existing = await self.repository.get_by_slug(slug)
            if existing is not None:
                raise ValueError(f"A game with slug '{slug}' already exists")

        game = Game(
            account_id=account_id,
            name=name,
            slug=slug,
            steam_app_id=steam_app_id,
            default_board_id=default_board_id,
            anti_cheat_enabled=anti_cheat_enabled,
            description=description,
            tags=tags or [],
            page_url=page_url,
        )

        created_game = await self.repository.create(game)
        logger.info(
            "Game created", game_id=str(created_game.id), account_id=str(account_id), slug=slug
        )
        return created_game

    async def get_game(self, game_id: GameID) -> Game | None:
        """Get a game by its ID.

        Args:
            game_id: The ID of the game to retrieve.

        Returns:
            The Game domain entity if found, None otherwise.
        """
        return await self.get_by_id(game_id)

    async def get_game_by_slug(self, slug: str) -> Game | None:
        """Get a game by its slug (globally unique).

        Args:
            slug: The game slug to search for.

        Returns:
            The Game domain entity if found, None otherwise.
        """
        return await self.repository.get_by_slug(slug)

    async def list_games(
        self,
        account_id: AccountID | None,
        *,
        pagination: PaginationParams,
    ) -> PaginatedResult[Game]:
        """List all games for an account with pagination.

        Args:
            account_id: The ID of the account to list games for. If None, returns all
                games (superadmin use case).
            pagination: Pagination parameters (required).

        Returns:
            PaginatedResult containing Game entities matching the filter criteria.
        """
        return await self.repository.filter(account_id, pagination=pagination)

    async def update_game(self, game_id: GameID, **updates: Any) -> Game:
        """Update game fields.

        Accepts any fields to update as keyword arguments. Only fields
        explicitly provided will be updated, allowing null values to
        clear optional fields.

        Args:
            game_id: The ID of the game to update
            **updates: Field names and values to update

        Returns:
            The updated Game domain entity

        Raises:
            EntityNotFoundError: If the game doesn't exist
        """
        game = await self.get_by_id_or_raise(game_id)

        for field, value in updates.items():
            setattr(game, field, value)

        return await self.repository.update(game)
