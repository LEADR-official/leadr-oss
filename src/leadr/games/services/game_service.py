"""Game service for managing game operations."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from leadr.common.services import BaseService
from leadr.games.domain.game import Game
from leadr.games.services.repositories import GameRepository


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
        account_id: UUID,
        name: str,
        steam_app_id: str | None = None,
        default_board_id: UUID | None = None,
    ) -> Game:
        """Create a new game.

        Args:
            account_id: The ID of the account that owns this game.
            name: The game name.
            steam_app_id: Optional Steam application ID.
            default_board_id: Optional default leaderboard ID.

        Returns:
            The created Game domain entity.

        Example:
            >>> game = await service.create_game(
            ...     account_id=account.id,
            ...     name="Super Awesome Game",
            ...     steam_app_id="123456",
            ... )
        """
        game = Game(
            account_id=account_id,
            name=name,
            steam_app_id=steam_app_id,
            default_board_id=default_board_id,
        )

        return await self.repository.create(game)

    async def get_game(self, game_id: UUID) -> Game | None:
        """Get a game by its ID.

        Args:
            game_id: The ID of the game to retrieve.

        Returns:
            The Game domain entity if found, None otherwise.
        """
        return await self.get_by_id(game_id)

    async def list_games(self, account_id: UUID) -> list[Game]:
        """List all games for an account.

        Args:
            account_id: The ID of the account to list games for.

        Returns:
            List of Game domain entities for the account.
        """
        return await self.repository.filter(account_id)

    async def update_game(
        self,
        game_id: UUID,
        name: str | None = None,
        steam_app_id: str | None = None,
        default_board_id: UUID | None = None,
    ) -> Game:
        """Update game fields.

        Args:
            game_id: The ID of the game to update
            name: New game name, if provided
            steam_app_id: New Steam app ID, if provided
            default_board_id: New default board ID, if provided

        Returns:
            The updated Game domain entity

        Raises:
            EntityNotFoundError: If the game doesn't exist
        """
        game = await self.get_by_id_or_raise(game_id)

        if name is not None:
            game.name = name
        if steam_app_id is not None:
            game.steam_app_id = steam_app_id
        if default_board_id is not None:
            game.default_board_id = default_board_id

        return await self.repository.update(game)
