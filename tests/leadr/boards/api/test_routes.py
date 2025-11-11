"""Tests for Board API routes."""

import pytest
from httpx import AsyncClient

from leadr.accounts.services.account_service import AccountService
from leadr.games.services.game_service import GameService


@pytest.mark.asyncio
class TestBoardRoutes:
    """Test suite for Board API routes."""

    async def test_create_board(self, client: AsyncClient, db_session, test_api_key):
        """Test creating a board via API."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board
        response = await client.post(
            "/boards",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Speed Run Board",
                "icon": "trophy",
                "short_code": "SR2025",
                "unit": "seconds",
                "is_active": True,
                "sort_direction": "ASCENDING",
                "keep_strategy": "BEST_ONLY",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Speed Run Board"
        assert data["short_code"] == "SR2025"
        assert data["account_id"] == str(account.id)
        assert data["game_id"] == str(game.id)
        assert "id" in data
        assert "created_at" in data

    async def test_create_board_with_optional_fields(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a board with optional fields via API."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board with optional fields
        response = await client.post(
            "/boards",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Speed Run Board",
                "icon": "trophy",
                "short_code": "SR2025",
                "unit": "seconds",
                "is_active": True,
                "sort_direction": "ASCENDING",
                "keep_strategy": "BEST_ONLY",
                "tags": ["speedrun", "no-damage"],
                "template_name": "Speed Run Template",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["tags"] == ["speedrun", "no-damage"]
        assert data["template_name"] == "Speed Run Template"

    async def test_create_board_with_game_not_found(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a board with non-existent game returns 404."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        response = await client.post(
            "/boards",
            json={
                "account_id": str(account.id),
                "game_id": "00000000-0000-0000-0000-000000000000",
                "name": "Invalid Board",
                "icon": "star",
                "short_code": "INVALID",
                "unit": "points",
                "is_active": True,
                "sort_direction": "DESCENDING",
                "keep_strategy": "ALL",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_create_board_with_game_from_different_account(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a board with game from different account returns 400."""
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

        # Create game for account1
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account1.id,
            name="Account 1 Game",
        )

        # Try to create board for account2 with account1's game
        response = await client.post(
            "/boards",
            json={
                "account_id": str(account2.id),
                "game_id": str(game.id),
                "name": "Invalid Board",
                "icon": "star",
                "short_code": "INVALID",
                "unit": "points",
                "is_active": True,
                "sort_direction": "DESCENDING",
                "keep_strategy": "ALL",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400
        assert "does not belong to account" in response.json()["detail"].lower()

    async def test_get_board(self, client: AsyncClient, db_session, test_api_key):
        """Test retrieving a board by ID via API."""
        # Create account, game, and board
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        create_response = await client.post(
            "/boards",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Speed Run Board",
                "icon": "trophy",
                "short_code": "SR2025",
                "unit": "seconds",
                "is_active": True,
                "sort_direction": "ASCENDING",
                "keep_strategy": "BEST_ONLY",
            },
            headers={"leadr-api-key": test_api_key},
        )
        board_id = create_response.json()["id"]

        # Retrieve it
        response = await client.get(f"/boards/{board_id}", headers={"leadr-api-key": test_api_key})

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == board_id
        assert data["name"] == "Speed Run Board"

    async def test_get_board_not_found(self, client: AsyncClient, test_api_key):
        """Test retrieving a non-existent board returns 404."""
        response = await client.get(
            "/boards/00000000-0000-0000-0000-000000000000",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_get_board_by_short_code(self, client: AsyncClient, db_session, test_api_key):
        """Test retrieving a board by short code via API."""
        # Create account, game, and board
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        create_response = await client.post(
            "/boards",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Speed Run Board",
                "icon": "trophy",
                "short_code": "SR2025",
                "unit": "seconds",
                "is_active": True,
                "sort_direction": "ASCENDING",
                "keep_strategy": "BEST_ONLY",
            },
            headers={"leadr-api-key": test_api_key},
        )
        board_id = create_response.json()["id"]

        # Retrieve by short code
        response = await client.get(
            "/boards/by-code/SR2025", headers={"leadr-api-key": test_api_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == board_id
        assert data["short_code"] == "SR2025"

    async def test_get_board_by_short_code_not_found(self, client: AsyncClient, test_api_key):
        """Test retrieving a board by non-existent short code returns 404."""
        response = await client.get(
            "/boards/by-code/NONEXISTENT", headers={"leadr-api-key": test_api_key}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_list_boards(self, client: AsyncClient, db_session, test_api_key):
        """Test listing boards for an account via API."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create multiple boards
        await client.post(
            "/boards",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Board One",
                "icon": "star",
                "short_code": "B001",
                "unit": "points",
                "is_active": True,
                "sort_direction": "DESCENDING",
                "keep_strategy": "ALL",
            },
            headers={"leadr-api-key": test_api_key},
        )
        await client.post(
            "/boards",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Board Two",
                "icon": "trophy",
                "short_code": "B002",
                "unit": "seconds",
                "is_active": True,
                "sort_direction": "ASCENDING",
                "keep_strategy": "BEST_ONLY",
            },
            headers={"leadr-api-key": test_api_key},
        )

        # List boards
        response = await client.get(
            f"/boards?account_id={account.id}", headers={"leadr-api-key": test_api_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        names = {b["name"] for b in data}
        assert "Board One" in names
        assert "Board Two" in names

    async def test_list_boards_requires_account_id(self, client: AsyncClient, test_api_key):
        """Test that listing boards requires account_id parameter."""
        response = await client.get("/boards", headers={"leadr-api-key": test_api_key})

        assert response.status_code == 422  # Validation error

    async def test_list_boards_filters_by_account(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that listing boards filters by account."""
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
        game1 = await game_service.create_game(
            account_id=account1.id,
            name="Game 1",
        )
        game2 = await game_service.create_game(
            account_id=account2.id,
            name="Game 2",
        )

        # Create boards for each account
        await client.post(
            "/boards",
            json={
                "account_id": str(account1.id),
                "game_id": str(game1.id),
                "name": "Account 1 Board",
                "icon": "star",
                "short_code": "A1B1",
                "unit": "points",
                "is_active": True,
                "sort_direction": "DESCENDING",
                "keep_strategy": "ALL",
            },
            headers={"leadr-api-key": test_api_key},
        )
        await client.post(
            "/boards",
            json={
                "account_id": str(account2.id),
                "game_id": str(game2.id),
                "name": "Account 2 Board",
                "icon": "trophy",
                "short_code": "A2B1",
                "unit": "seconds",
                "is_active": True,
                "sort_direction": "ASCENDING",
                "keep_strategy": "BEST_ONLY",
            },
            headers={"leadr-api-key": test_api_key},
        )

        # List boards for account 1
        response = await client.get(
            f"/boards?account_id={account1.id}", headers={"leadr-api-key": test_api_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Account 1 Board"

    async def test_update_board(self, client: AsyncClient, db_session, test_api_key):
        """Test updating a board via API."""
        # Create account, game, and board
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        create_response = await client.post(
            "/boards",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Speed Run Board",
                "icon": "trophy",
                "short_code": "SR2025",
                "unit": "seconds",
                "is_active": True,
                "sort_direction": "ASCENDING",
                "keep_strategy": "BEST_ONLY",
            },
            headers={"leadr-api-key": test_api_key},
        )
        board_id = create_response.json()["id"]

        # Update it
        response = await client.patch(
            f"/boards/{board_id}",
            json={
                "name": "Updated Speed Run Board",
                "is_active": False,
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Speed Run Board"
        assert data["is_active"] is False
        assert data["icon"] == "trophy"  # Unchanged

    async def test_update_board_not_found(self, client: AsyncClient, test_api_key):
        """Test updating a non-existent board returns 404."""
        response = await client.patch(
            "/boards/00000000-0000-0000-0000-000000000000",
            json={"name": "New Name"},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_soft_delete_board(self, client: AsyncClient, db_session, test_api_key):
        """Test soft-deleting a board via API."""
        # Create account, game, and board
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        create_response = await client.post(
            "/boards",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Speed Run Board",
                "icon": "trophy",
                "short_code": "SR2025",
                "unit": "seconds",
                "is_active": True,
                "sort_direction": "ASCENDING",
                "keep_strategy": "BEST_ONLY",
            },
            headers={"leadr-api-key": test_api_key},
        )
        board_id = create_response.json()["id"]

        # Soft-delete it
        response = await client.patch(
            f"/boards/{board_id}",
            json={"deleted": True},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == board_id

        # Verify it's not returned by get
        get_response = await client.get(
            f"/boards/{board_id}", headers={"leadr-api-key": test_api_key}
        )
        assert get_response.status_code == 404

    async def test_list_boards_excludes_deleted(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that list endpoint excludes soft-deleted boards."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create boards
        board1_response = await client.post(
            "/boards",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Board One",
                "icon": "star",
                "short_code": "B001",
                "unit": "points",
                "is_active": True,
                "sort_direction": "DESCENDING",
                "keep_strategy": "ALL",
            },
            headers={"leadr-api-key": test_api_key},
        )
        board1_id = board1_response.json()["id"]

        await client.post(
            "/boards",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Board Two",
                "icon": "trophy",
                "short_code": "B002",
                "unit": "seconds",
                "is_active": True,
                "sort_direction": "ASCENDING",
                "keep_strategy": "BEST_ONLY",
            },
            headers={"leadr-api-key": test_api_key},
        )

        # Soft-delete one
        await client.patch(
            f"/boards/{board1_id}", json={"deleted": True}, headers={"leadr-api-key": test_api_key}
        )

        # List should only return non-deleted
        response = await client.get(
            f"/boards?account_id={account.id}", headers={"leadr-api-key": test_api_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Board Two"
