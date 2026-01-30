"""Tests for Game API routes."""

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError

from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import AccountID, GameID
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.games.domain.game import Game


@pytest.mark.asyncio
class TestGameRoutes:
    """Test suite for Game API routes."""

    async def test_create_game(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service, mock_hooks
    ):
        """Test creating a game via API."""
        # Arrange
        account_id = admin_auth.account_id
        game = Game(
            account_id=account_id,
            name="Super Awesome Game",
            slug="super-awesome-game",
            steam_app_id="123456",
        )
        mock_game_service.create_game.return_value = game

        # Act
        response = await mock_client_no_db.post(
            "/games",
            json={
                "account_id": str(account_id),
                "name": "Super Awesome Game",
                "slug": "super-awesome-game",
                "steam_app_id": "123456",
            },
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Super Awesome Game"
        assert data["steam_app_id"] == "123456"
        assert data["account_id"] == str(account_id)
        assert "id" in data
        assert "created_at" in data

        mock_game_service.create_game.assert_called_once_with(
            account_id=account_id,
            name="Super Awesome Game",
            slug="super-awesome-game",
            steam_app_id="123456",
            default_board_id=None,
            anti_cheat_enabled=True,
            description=None,
            tags=None,
            page_url=None,
        )
        mock_hooks["pre_create"].assert_called_once()
        mock_hooks["post_create"].assert_called_once()

    async def test_create_game_with_account_not_found(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service, mock_hooks
    ):
        """Test creating a game with non-existent account returns 404."""
        # Arrange
        mock_game_service.create_game.side_effect = IntegrityError(
            "statement", "params", Exception("orig")
        )

        # Act
        response = await mock_client_no_db.post(
            "/games",
            json={
                "account_id": "acc_00000000-0000-0000-0000-000000000000",
                "name": "Super Awesome Game",
                "slug": "super-awesome-game",
            },
        )

        # Assert
        assert response.status_code == 404
        assert "Account not found" in response.json()["error"]

    async def test_get_game(self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service):
        """Test retrieving a game by ID via API."""
        # Arrange
        account_id = admin_auth.account_id
        game_id = GameID()
        game = Game(
            id=game_id,
            account_id=account_id,
            name="Super Awesome Game",
            slug="super-awesome-game",
        )
        mock_game_service.get_by_id_or_raise.return_value = game

        # Act
        response = await mock_client_no_db.get(f"/games/{game_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(game_id)
        assert data["name"] == "Super Awesome Game"

        mock_game_service.get_by_id_or_raise.assert_called_once_with(game_id)

    async def test_get_game_not_found(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service
    ):
        """Test retrieving a non-existent game returns 404."""
        # Arrange
        game_id = GameID()
        mock_game_service.get_by_id_or_raise.side_effect = EntityNotFoundError("Game", str(game_id))

        # Act
        response = await mock_client_no_db.get(f"/games/{game_id}")

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()

    async def test_list_games(self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service):
        """Test listing games for an account via API."""
        # Arrange
        account_id = admin_auth.account_id
        games = [
            Game(account_id=account_id, name="Game One", slug="game-one"),
            Game(account_id=account_id, name="Game Two", slug="game-two"),
        ]
        result = PaginatedResult(
            items=games,
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        mock_game_service.list_games.return_value = result

        # Act
        response = await mock_client_no_db.get(f"/games?account_id={account_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 2
        names = {g["name"] for g in data["data"]}
        assert "Game One" in names
        assert "Game Two" in names

    async def test_list_games_filters_by_account(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service
    ):
        """Test that listing games filters by account."""
        # Arrange
        account_id = AccountID()
        games = [Game(account_id=account_id, name="Account 1 Game", slug="account-1-game")]
        result = PaginatedResult(
            items=games,
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        mock_game_service.list_games.return_value = result

        # Act
        response = await mock_client_no_db.get(f"/games?account_id={account_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Account 1 Game"

    async def test_update_game(self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service):
        """Test updating a game via API."""
        # Arrange
        account_id = admin_auth.account_id
        game_id = GameID()
        original_game = Game(
            id=game_id,
            account_id=account_id,
            name="Super Awesome Game",
            slug="super-awesome-game",
        )
        updated_game = Game(
            id=game_id,
            account_id=account_id,
            name="Ultra Awesome Game",
            slug="super-awesome-game",
            steam_app_id="999999",
        )
        mock_game_service.get_by_id_or_raise.return_value = original_game
        mock_game_service.update_game.return_value = updated_game

        # Act
        response = await mock_client_no_db.patch(
            f"/games/{game_id}",
            json={
                "name": "Ultra Awesome Game",
                "steam_app_id": "999999",
            },
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Ultra Awesome Game"
        assert data["steam_app_id"] == "999999"

        mock_game_service.get_by_id_or_raise.assert_called_once_with(game_id)
        mock_game_service.update_game.assert_called_once_with(
            game_id, name="Ultra Awesome Game", steam_app_id="999999"
        )

    async def test_update_game_not_found(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service
    ):
        """Test updating a non-existent game returns 404."""
        # Arrange
        game_id = GameID()
        mock_game_service.get_by_id_or_raise.side_effect = EntityNotFoundError("Game", str(game_id))

        # Act
        response = await mock_client_no_db.patch(
            f"/games/{game_id}",
            json={"name": "New Name"},
        )

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()

    async def test_soft_delete_game(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service
    ):
        """Test soft-deleting a game via API."""
        # Arrange
        account_id = admin_auth.account_id
        game_id = GameID()
        game = Game(
            id=game_id,
            account_id=account_id,
            name="Super Awesome Game",
            slug="super-awesome-game",
        )
        mock_game_service.get_by_id_or_raise.return_value = game
        mock_game_service.soft_delete.return_value = game

        # Act
        response = await mock_client_no_db.patch(
            f"/games/{game_id}",
            json={"deleted": True},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(game_id)

        mock_game_service.soft_delete.assert_called_once_with(game_id)

    async def test_list_games_excludes_deleted(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service
    ):
        """Test that list endpoint excludes soft-deleted games."""
        # Arrange
        account_id = admin_auth.account_id
        games = [Game(account_id=account_id, name="Game Two", slug="game-two")]
        result = PaginatedResult(
            items=games,
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        mock_game_service.list_games.return_value = result

        # Act
        response = await mock_client_no_db.get(f"/games?account_id={account_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Game Two"

    async def test_create_game_with_anti_cheat_enabled_default(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service, mock_hooks
    ):
        """Test that anti_cheat_enabled defaults to True when creating a game."""
        # Arrange
        account_id = admin_auth.account_id
        game = Game(
            account_id=account_id,
            name="Super Awesome Game",
            slug="super-awesome-game",
            anti_cheat_enabled=True,
        )
        mock_game_service.create_game.return_value = game

        # Act
        response = await mock_client_no_db.post(
            "/games",
            json={
                "account_id": str(account_id),
                "name": "Super Awesome Game",
                "slug": "super-awesome-game",
            },
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["anti_cheat_enabled"] is True

    async def test_create_game_with_anti_cheat_disabled(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service, mock_hooks
    ):
        """Test creating a game with anti_cheat_enabled explicitly set to False."""
        # Arrange
        account_id = admin_auth.account_id
        game = Game(
            account_id=account_id,
            name="Custom Anti-Cheat Game",
            slug="custom-anti-cheat-game",
            anti_cheat_enabled=False,
        )
        mock_game_service.create_game.return_value = game

        # Act
        response = await mock_client_no_db.post(
            "/games",
            json={
                "account_id": str(account_id),
                "name": "Custom Anti-Cheat Game",
                "slug": "custom-anti-cheat-game",
                "anti_cheat_enabled": False,
            },
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Custom Anti-Cheat Game"
        assert data["anti_cheat_enabled"] is False

    async def test_update_game_anti_cheat_enabled(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service
    ):
        """Test updating a game's anti_cheat_enabled field."""
        # Arrange
        account_id = admin_auth.account_id
        game_id = GameID()
        original_game = Game(
            id=game_id,
            account_id=account_id,
            name="Game to Update",
            slug="game-to-update",
            anti_cheat_enabled=True,
        )
        disabled_game = Game(
            id=game_id,
            account_id=account_id,
            name="Game to Update",
            slug="game-to-update",
            anti_cheat_enabled=False,
        )
        enabled_game = Game(
            id=game_id,
            account_id=account_id,
            name="Game to Update",
            slug="game-to-update",
            anti_cheat_enabled=True,
        )
        mock_game_service.get_by_id_or_raise.return_value = original_game
        mock_game_service.update_game.side_effect = [disabled_game, enabled_game]

        # Act - Disable anti-cheat
        response1 = await mock_client_no_db.patch(
            f"/games/{game_id}",
            json={"anti_cheat_enabled": False},
        )

        # Assert
        assert response1.status_code == 200
        assert response1.json()["anti_cheat_enabled"] is False

        # Act - Re-enable anti-cheat
        response2 = await mock_client_no_db.patch(
            f"/games/{game_id}",
            json={"anti_cheat_enabled": True},
        )

        # Assert
        assert response2.status_code == 200
        assert response2.json()["anti_cheat_enabled"] is True

    async def test_get_game_includes_anti_cheat_enabled(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service
    ):
        """Test that retrieving a game includes the anti_cheat_enabled field."""
        # Arrange
        account_id = admin_auth.account_id
        game_id = GameID()
        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
            anti_cheat_enabled=False,
        )
        mock_game_service.get_by_id_or_raise.return_value = game

        # Act
        response = await mock_client_no_db.get(f"/games/{game_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "anti_cheat_enabled" in data
        assert data["anti_cheat_enabled"] is False

    async def test_superadmin_list_games_without_account_id_returns_all(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service
    ):
        """Test that superadmin can list games WITHOUT account_id and sees all accounts."""
        # Arrange
        account1_id = AccountID()
        account2_id = AccountID()

        games = [
            Game(account_id=account1_id, name="Game from Account 1", slug="game-from-account-1"),
            Game(account_id=account2_id, name="Game from Account 2", slug="game-from-account-2"),
        ]
        result = PaginatedResult(
            items=games,
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        mock_game_service.list_games.return_value = result

        # Act
        response = await mock_client_no_db.get("/games")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

        # Should contain games from both accounts
        game_names = {g["name"] for g in data["data"]}
        assert "Game from Account 1" in game_names
        assert "Game from Account 2" in game_names

    async def test_create_game_with_tags_and_description(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service, mock_hooks
    ):
        """Test creating a game with tags and description via API."""
        # Arrange
        account_id = admin_auth.account_id
        game = Game(
            account_id=account_id,
            name="Adventure Game",
            slug="adventure-game",
            description="An epic journey awaits",
            tags=["adventure", "rpg", "story"],
        )
        mock_game_service.create_game.return_value = game

        # Act
        response = await mock_client_no_db.post(
            "/games",
            json={
                "account_id": str(account_id),
                "name": "Adventure Game",
                "slug": "adventure-game",
                "description": "An epic journey awaits",
                "tags": ["adventure", "rpg", "story"],
            },
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Adventure Game"
        assert data["description"] == "An epic journey awaits"
        assert data["tags"] == ["adventure", "rpg", "story"]

    async def test_create_game_tags_defaults_to_empty_list(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service, mock_hooks
    ):
        """Test that tags defaults to empty list when not provided via API."""
        # Arrange
        account_id = admin_auth.account_id
        game = Game(
            account_id=account_id,
            name="Simple Game",
            slug="simple-game",
            tags=[],
            description=None,
        )
        mock_game_service.create_game.return_value = game

        # Act
        response = await mock_client_no_db.post(
            "/games",
            json={
                "account_id": str(account_id),
                "name": "Simple Game",
                "slug": "simple-game",
            },
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["tags"] == []
        assert data["description"] is None

    async def test_update_game_tags(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service
    ):
        """Test updating a game's tags via API."""
        # Arrange
        account_id = admin_auth.account_id
        game_id = GameID()
        original_game = Game(
            id=game_id,
            account_id=account_id,
            name="Game to Update Tags",
            slug="game-to-update-tags",
        )
        updated_game = Game(
            id=game_id,
            account_id=account_id,
            name="Game to Update Tags",
            slug="game-to-update-tags",
            tags=["action", "puzzle"],
        )
        mock_game_service.get_by_id_or_raise.return_value = original_game
        mock_game_service.update_game.return_value = updated_game

        # Act
        response = await mock_client_no_db.patch(
            f"/games/{game_id}",
            json={"tags": ["action", "puzzle"]},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["tags"] == ["action", "puzzle"]

    async def test_update_game_description(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service
    ):
        """Test updating a game's description via API."""
        # Arrange
        account_id = admin_auth.account_id
        game_id = GameID()
        original_game = Game(
            id=game_id,
            account_id=account_id,
            name="Game to Update Description",
            slug="game-to-update-description",
        )
        updated_game = Game(
            id=game_id,
            account_id=account_id,
            name="Game to Update Description",
            slug="game-to-update-description",
            description="A brand new description",
        )
        mock_game_service.get_by_id_or_raise.return_value = original_game
        mock_game_service.update_game.return_value = updated_game

        # Act
        response = await mock_client_no_db.patch(
            f"/games/{game_id}",
            json={"description": "A brand new description"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "A brand new description"

    async def test_get_game_returns_tags_and_description(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service
    ):
        """Test that retrieving a game includes tags and description."""
        # Arrange
        account_id = admin_auth.account_id
        game_id = GameID()
        game = Game(
            id=game_id,
            account_id=account_id,
            name="Full Game",
            slug="full-game",
            description="A complete game",
            tags=["complete", "full"],
        )
        mock_game_service.get_by_id_or_raise.return_value = game

        # Act
        response = await mock_client_no_db.get(f"/games/{game_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "A complete game"
        assert data["tags"] == ["complete", "full"]

    async def test_create_game_with_page_url(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service, mock_hooks
    ):
        """Test creating a game with page_url via API."""
        # Arrange
        account_id = admin_auth.account_id
        game = Game(
            account_id=account_id,
            name="Game with Page",
            slug="game-with-page",
            page_url="https://example.com/game",
        )
        mock_game_service.create_game.return_value = game

        # Act
        response = await mock_client_no_db.post(
            "/games",
            json={
                "account_id": str(account_id),
                "name": "Game with Page",
                "slug": "game-with-page",
                "page_url": "https://example.com/game",
            },
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Game with Page"
        assert data["page_url"] == "https://example.com/game"

    async def test_update_game_page_url(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service
    ):
        """Test updating a game's page_url via API."""
        # Arrange
        account_id = admin_auth.account_id
        game_id = GameID()
        original_game = Game(
            id=game_id,
            account_id=account_id,
            name="Game to Update URL",
            slug="game-to-update-url",
        )
        updated_game = Game(
            id=game_id,
            account_id=account_id,
            name="Game to Update URL",
            slug="game-to-update-url",
            page_url="https://example.com/updated",
        )
        mock_game_service.get_by_id_or_raise.return_value = original_game
        mock_game_service.update_game.return_value = updated_game

        # Act
        response = await mock_client_no_db.patch(
            f"/games/{game_id}",
            json={"page_url": "https://example.com/updated"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["page_url"] == "https://example.com/updated"

    async def test_game_page_url_defaults_to_none(
        self, mock_client_no_db: AsyncClient, admin_auth, mock_game_service, mock_hooks
    ):
        """Test that page_url defaults to None when not provided via API."""
        # Arrange
        account_id = admin_auth.account_id
        game = Game(
            account_id=account_id,
            name="Simple Game",
            slug="simple-game",
            page_url=None,
        )
        mock_game_service.create_game.return_value = game

        # Act
        response = await mock_client_no_db.post(
            "/games",
            json={
                "account_id": str(account_id),
                "name": "Simple Game",
                "slug": "simple-game",
            },
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["page_url"] is None
