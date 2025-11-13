"""Tests for Game service."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.services.account_service import AccountService
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import GameID
from leadr.games.services.game_service import GameService


@pytest.mark.asyncio
class TestGameService:
    """Test suite for Game service."""

    async def test_create_game(self, db_session: AsyncSession):
        """Test creating a game via service."""
        # Create account first
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Create game
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Super Awesome Game",
            steam_app_id="123456",
        )

        assert game.id is not None
        assert game.account_id == account.id
        assert game.name == "Super Awesome Game"
        assert game.steam_app_id == "123456"
        assert game.default_board_id is None

    async def test_create_game_with_minimal_fields(self, db_session: AsyncSession):
        """Test creating a game with only required fields."""
        # Create account first
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Create game with only required fields
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Simple Game",
        )

        assert game.id is not None
        assert game.account_id == account.id
        assert game.name == "Simple Game"
        assert game.steam_app_id is None
        assert game.default_board_id is None

    async def test_get_game(self, db_session: AsyncSession):
        """Test retrieving a game by ID via service."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        created_game = await game_service.create_game(
            account_id=account.id,
            name="Super Awesome Game",
        )

        # Retrieve it
        game = await game_service.get_game(created_game.id)

        assert game is not None
        assert game.id == created_game.id
        assert game.name == "Super Awesome Game"

    async def test_get_game_not_found(self, db_session: AsyncSession):
        """Test retrieving a non-existent game returns None."""
        game_service = GameService(db_session)
        non_existent_id = uuid4()

        game = await game_service.get_game(GameID(non_existent_id))

        assert game is None

    async def test_list_games(self, db_session: AsyncSession):
        """Test listing all games for an account."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Create multiple games
        game_service = GameService(db_session)
        await game_service.create_game(
            account_id=account.id,
            name="Game One",
        )
        await game_service.create_game(
            account_id=account.id,
            name="Game Two",
        )

        # List them
        games = await game_service.list_games(account.id)

        assert len(games) == 2
        names = {g.name for g in games}
        assert "Game One" in names
        assert "Game Two" in names

    async def test_list_games_filters_by_account(self, db_session: AsyncSession):
        """Test that list_games only returns games for the specified account."""
        # Create two accounts
        account_service = AccountService(db_session)
        account1 = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )
        account2 = await account_service.create_account(
            name="Beta Industries",
            slug="beta-industries",
        )

        # Create games for each account
        game_service = GameService(db_session)
        await game_service.create_game(
            account_id=account1.id,
            name="Account 1 Game",
        )
        await game_service.create_game(
            account_id=account2.id,
            name="Account 2 Game",
        )

        # List games for account 1
        games = await game_service.list_games(account1.id)

        assert len(games) == 1
        assert games[0].name == "Account 1 Game"
        assert games[0].account_id == account1.id

    async def test_update_game(self, db_session: AsyncSession):
        """Test updating a game via service."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        created_game = await game_service.create_game(
            account_id=account.id,
            name="Super Awesome Game",
        )

        # Update it
        updated_game = await game_service.update_game(
            game_id=created_game.id,
            name="Ultra Awesome Game",
            steam_app_id="999999",
        )

        assert updated_game.name == "Ultra Awesome Game"
        assert updated_game.steam_app_id == "999999"

        # Verify in database
        game = await game_service.get_game(created_game.id)
        assert game is not None
        assert game.name == "Ultra Awesome Game"
        assert game.steam_app_id == "999999"

    async def test_update_game_partial_fields(self, db_session: AsyncSession):
        """Test updating only some fields of a game."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        created_game = await game_service.create_game(
            account_id=account.id,
            name="Super Awesome Game",
            steam_app_id="123456",
        )

        # Update only the name
        updated_game = await game_service.update_game(
            game_id=created_game.id,
            name="New Name",
        )

        assert updated_game.name == "New Name"
        assert updated_game.steam_app_id == "123456"  # Unchanged

    async def test_update_game_not_found(self, db_session: AsyncSession):
        """Test that updating a non-existent game raises an error."""
        game_service = GameService(db_session)
        non_existent_id = uuid4()

        with pytest.raises(EntityNotFoundError) as exc_info:
            await game_service.update_game(
                game_id=GameID(non_existent_id),
                name="New Name",
            )

        assert "Game not found" in str(exc_info.value)

    async def test_soft_delete_game(self, db_session: AsyncSession):
        """Test soft-deleting a game via service."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        created_game = await game_service.create_game(
            account_id=account.id,
            name="Super Awesome Game",
        )

        # Soft-delete it (returns entity before deletion)
        deleted_game = await game_service.soft_delete(created_game.id)

        assert deleted_game.id == created_game.id
        assert deleted_game.is_deleted is False  # Returns entity before deletion

        # Verify it's not returned by get
        game = await game_service.get_game(created_game.id)
        assert game is None

    async def test_list_games_excludes_deleted(self, db_session: AsyncSession):
        """Test that list_games excludes soft-deleted games."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Create games
        game_service = GameService(db_session)
        game1 = await game_service.create_game(
            account_id=account.id,
            name="Game One",
        )
        await game_service.create_game(
            account_id=account.id,
            name="Game Two",
        )

        # Soft-delete one
        await game_service.soft_delete(game1.id)

        # List should only return non-deleted
        games = await game_service.list_games(account.id)

        assert len(games) == 1
        assert games[0].name == "Game Two"

    async def test_soft_delete_game_not_found(self, db_session: AsyncSession):
        """Test that soft-deleting a non-existent game raises an error."""
        game_service = GameService(db_session)
        non_existent_id = uuid4()

        with pytest.raises(EntityNotFoundError) as exc_info:
            await game_service.soft_delete(non_existent_id)

        assert "Game not found" in str(exc_info.value)
