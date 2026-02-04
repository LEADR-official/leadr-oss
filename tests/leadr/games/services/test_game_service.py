"""Tests for Game service."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from leadr.common.api.pagination import PaginatedResult, PaginationParams
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import AccountID, GameID
from leadr.games.domain.game import Game
from leadr.games.services.game_service import GameService


@pytest.mark.asyncio
class TestGameService:
    """Test suite for Game service."""

    @pytest.fixture
    def service(self, mock_session):
        """Create GameService with mock repository."""
        mock_repo = MagicMock()
        return GameService(mock_session, repository=mock_repo)

    async def test_create_game(self, service):
        """Test creating a game via service."""
        account_id = AccountID(uuid4())

        # Mock repository methods
        service.repository.get_by_slug = AsyncMock(return_value=None)
        service.repository.create = AsyncMock(side_effect=lambda entity: entity)

        # Create game
        game = await service.create_game(
            account_id=account_id,
            name="Super Awesome Game",
            steam_app_id="123456",
        )

        assert game.id is not None
        assert game.account_id == account_id
        assert game.name == "Super Awesome Game"
        assert game.steam_app_id == "123456"
        assert game.default_board_id is None
        service.repository.create.assert_called_once()

    async def test_create_game_with_minimal_fields(self, service):
        """Test creating a game with only required fields."""
        account_id = AccountID(uuid4())

        # Mock repository methods
        service.repository.get_by_slug = AsyncMock(return_value=None)
        service.repository.create = AsyncMock(side_effect=lambda entity: entity)

        # Create game with only required fields
        game = await service.create_game(
            account_id=account_id,
            name="Simple Game",
        )

        assert game.id is not None
        assert game.account_id == account_id
        assert game.name == "Simple Game"
        assert game.steam_app_id is None
        assert game.default_board_id is None
        service.repository.create.assert_called_once()

    async def test_get_game(self, service):
        """Test retrieving a game by ID via service."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        mock_game = Game(
            id=game_id,
            account_id=account_id,
            name="Super Awesome Game",
            slug="super-awesome-game",
        )

        # Mock repository method
        service.repository.get_by_id = AsyncMock(return_value=mock_game)

        # Retrieve it
        game = await service.get_game(game_id)

        assert game is not None
        assert game.id == game_id
        assert game.name == "Super Awesome Game"
        service.repository.get_by_id.assert_called_once()

    async def test_get_game_not_found(self, service):
        """Test retrieving a non-existent game returns None."""
        non_existent_id = GameID(uuid4())

        # Mock repository method
        service.repository.get_by_id = AsyncMock(return_value=None)

        game = await service.get_game(non_existent_id)

        assert game is None
        service.repository.get_by_id.assert_called_once()

    async def test_list_games(self, service):
        """Test listing all games for an account."""
        account_id = AccountID(uuid4())
        game1 = Game(
            id=GameID(uuid4()),
            account_id=account_id,
            name="Game One",
            slug="game-one",
        )
        game2 = Game(
            id=GameID(uuid4()),
            account_id=account_id,
            name="Game Two",
            slug="game-two",
        )

        # Mock repository method
        mock_result = PaginatedResult(
            items=[game1, game2],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        service.repository.filter = AsyncMock(return_value=mock_result)

        # List them
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.list_games(account_id, pagination=pagination)

        assert len(result.items) == 2
        names = {g.name for g in result.items}
        assert "Game One" in names
        assert "Game Two" in names
        service.repository.filter.assert_called_once_with(account_id, pagination=pagination)

    async def test_list_games_filters_by_account(self, service):
        """Test that list_games only returns games for the specified account."""
        account1_id = AccountID(uuid4())

        game1 = Game(
            id=GameID(uuid4()),
            account_id=account1_id,
            name="Account 1 Game",
            slug="account-1-game",
        )

        # Mock repository method
        mock_result = PaginatedResult(
            items=[game1],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        service.repository.filter = AsyncMock(return_value=mock_result)

        # List games for account 1
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.list_games(account1_id, pagination=pagination)

        assert len(result.items) == 1
        assert result.items[0].name == "Account 1 Game"
        assert result.items[0].account_id == account1_id
        service.repository.filter.assert_called_once_with(account1_id, pagination=pagination)

    async def test_update_game(self, service):
        """Test updating a game via service."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        existing_game = Game(
            id=game_id,
            account_id=account_id,
            name="Super Awesome Game",
            slug="super-awesome-game",
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=existing_game)
        service.repository.update = AsyncMock(side_effect=lambda entity: entity)

        # Update it
        updated_game = await service.update_game(
            game_id=game_id,
            name="Ultra Awesome Game",
            steam_app_id="999999",
        )

        assert updated_game.name == "Ultra Awesome Game"
        assert updated_game.steam_app_id == "999999"
        service.repository.get_by_id.assert_called_once()
        service.repository.update.assert_called_once()

    async def test_update_game_partial_fields(self, service):
        """Test updating only some fields of a game."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        existing_game = Game(
            id=game_id,
            account_id=account_id,
            name="Super Awesome Game",
            slug="super-awesome-game",
            steam_app_id="123456",
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=existing_game)
        service.repository.update = AsyncMock(side_effect=lambda entity: entity)

        # Update only the name
        updated_game = await service.update_game(
            game_id=game_id,
            name="New Name",
        )

        assert updated_game.name == "New Name"
        assert updated_game.steam_app_id == "123456"  # Unchanged
        service.repository.get_by_id.assert_called_once()
        service.repository.update.assert_called_once()

    async def test_update_game_not_found(self, service):
        """Test that updating a non-existent game raises an error."""
        non_existent_id = GameID(uuid4())

        # Mock repository method
        service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError) as exc_info:
            await service.update_game(
                game_id=non_existent_id,
                name="New Name",
            )

        assert "Game not found" in str(exc_info.value)
        service.repository.get_by_id.assert_called_once()

    async def test_soft_delete_game(self, service):
        """Test soft-deleting a game via service."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        existing_game = Game(
            id=game_id,
            account_id=account_id,
            name="Super Awesome Game",
            slug="super-awesome-game",
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=existing_game)
        service.repository.delete = AsyncMock()

        # Soft-delete it (returns entity before deletion)
        deleted_game = await service.soft_delete(game_id)

        assert deleted_game.id == game_id
        assert deleted_game.is_deleted is False  # Returns entity before deletion
        service.repository.get_by_id.assert_called_once()
        service.repository.delete.assert_called_once()

    async def test_list_games_excludes_deleted(self, service):
        """Test that list_games excludes soft-deleted games."""
        account_id = AccountID(uuid4())
        game2 = Game(
            id=GameID(uuid4()),
            account_id=account_id,
            name="Game Two",
            slug="game-two",
        )

        # Mock repository to return only non-deleted game
        mock_result = PaginatedResult(
            items=[game2],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        service.repository.filter = AsyncMock(return_value=mock_result)

        # List should only return non-deleted
        pagination = PaginationParams(cursor=None, limit=100, sort=None)
        result = await service.list_games(account_id, pagination=pagination)

        assert len(result.items) == 1
        assert result.items[0].name == "Game Two"
        service.repository.filter.assert_called_once_with(account_id, pagination=pagination)

    async def test_soft_delete_game_not_found(self, service):
        """Test that soft-deleting a non-existent game raises an error."""
        non_existent_id = GameID(uuid4())

        # Mock repository method
        service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError) as exc_info:
            await service.soft_delete(non_existent_id)

        assert "Game not found" in str(exc_info.value)
        service.repository.get_by_id.assert_called_once()

    async def test_create_game_with_tags_and_description(self, service):
        """Test creating a game with tags and description via service."""
        account_id = AccountID(uuid4())

        # Mock repository methods
        service.repository.get_by_slug = AsyncMock(return_value=None)
        service.repository.create = AsyncMock(side_effect=lambda entity: entity)

        game = await service.create_game(
            account_id=account_id,
            name="Adventure Game",
            description="An epic adventure awaits",
            tags=["adventure", "story", "rpg"],
        )

        assert game.id is not None
        assert game.description == "An epic adventure awaits"
        assert game.tags == ["adventure", "story", "rpg"]
        service.repository.create.assert_called_once()

    async def test_game_tags_defaults_to_empty_list(self, service):
        """Test that tags defaults to empty list when not provided via service."""
        account_id = AccountID(uuid4())

        # Mock repository methods
        service.repository.get_by_slug = AsyncMock(return_value=None)
        service.repository.create = AsyncMock(side_effect=lambda entity: entity)

        game = await service.create_game(
            account_id=account_id,
            name="Simple Game",
        )

        assert game.tags == []
        assert isinstance(game.tags, list)
        service.repository.create.assert_called_once()

    async def test_update_game_tags(self, service):
        """Test updating game tags."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        existing_game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=existing_game)
        service.repository.update = AsyncMock(side_effect=lambda entity: entity)

        # Update tags
        updated_game = await service.update_game(
            game_id=game_id,
            tags=["puzzle", "strategy"],
        )

        assert updated_game.tags == ["puzzle", "strategy"]
        assert updated_game.name == "Test Game"  # Unchanged
        service.repository.get_by_id.assert_called_once()
        service.repository.update.assert_called_once()

    async def test_update_game_description(self, service):
        """Test updating game description."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        existing_game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=existing_game)
        service.repository.update = AsyncMock(side_effect=lambda entity: entity)

        # Update description
        updated_game = await service.update_game(
            game_id=game_id,
            description="A brand new description",
        )

        assert updated_game.description == "A brand new description"
        assert updated_game.name == "Test Game"  # Unchanged
        service.repository.get_by_id.assert_called_once()
        service.repository.update.assert_called_once()

    async def test_game_tags_persists_through_retrieval(self, service):
        """Test that tags are persisted and retrieved correctly."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        mock_game = Game(
            id=game_id,
            account_id=account_id,
            name="Tagged Game",
            slug="tagged-game",
            tags=["tag1", "tag2", "tag3"],
        )

        # Mock repository method
        service.repository.get_by_id = AsyncMock(return_value=mock_game)

        # Retrieve the game
        retrieved_game = await service.get_game(game_id)

        assert retrieved_game is not None
        assert retrieved_game.tags == ["tag1", "tag2", "tag3"]
        service.repository.get_by_id.assert_called_once()

    async def test_create_game_slug_skips_soft_deleted_slugs(self, service):
        """Slug generation must detect soft-deleted slugs to avoid uq_game_slug violation."""
        account_id = AccountID(uuid4())

        # "pong" exists (active), "pong-2" exists (soft-deleted but still holds the slug)
        async def mock_get_by_slug(slug: str, include_deleted: bool = False) -> Game | None:
            active_slugs = {"pong"}
            deleted_slugs = {"pong-2"}
            if slug in active_slugs:
                return Game(id=GameID(uuid4()), account_id=account_id, name="Pong", slug=slug)
            if include_deleted and slug in deleted_slugs:
                return Game(id=GameID(uuid4()), account_id=account_id, name="Pong", slug=slug)
            return None

        service.repository.get_by_slug = mock_get_by_slug
        service.repository.create = AsyncMock(side_effect=lambda entity: entity)

        game = await service.create_game(account_id=account_id, name="Pong")

        # Should skip "pong" (active) and "pong-2" (deleted) and land on "pong-3"
        assert game.slug == "pong-3"

    async def test_create_game_with_page_url(self, service):
        """Test creating a game with page_url via service."""
        account_id = AccountID(uuid4())

        # Mock repository methods
        service.repository.get_by_slug = AsyncMock(return_value=None)
        service.repository.create = AsyncMock(side_effect=lambda entity: entity)

        game = await service.create_game(
            account_id=account_id,
            name="Game with Page",
            page_url="https://example.com/game",
        )

        assert game.id is not None
        assert game.page_url == "https://example.com/game"
        service.repository.create.assert_called_once()

    async def test_update_game_page_url(self, service):
        """Test updating game page_url."""
        game_id = GameID(uuid4())
        account_id = AccountID(uuid4())
        existing_game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
        )

        # Mock repository methods
        service.repository.get_by_id = AsyncMock(return_value=existing_game)
        service.repository.update = AsyncMock(side_effect=lambda entity: entity)

        # Update page_url
        updated_game = await service.update_game(
            game_id=game_id,
            page_url="https://example.com/updated-game",
        )

        assert updated_game.page_url == "https://example.com/updated-game"
        assert updated_game.name == "Test Game"  # Unchanged
        service.repository.get_by_id.assert_called_once()
        service.repository.update.assert_called_once()
