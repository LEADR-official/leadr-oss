"""Tests for Board API routes."""

import logging

import pytest
from httpx import AsyncClient

from leadr.accounts.services.account_service import AccountService
from leadr.games.services.game_service import GameService

logger = logging.getLogger(__name__)


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

    async def test_create_board_with_minimal_fields(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a board with minimal required fields using defaults."""
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

        # Create board with only required fields (name)
        # Other fields should use defaults from the schema
        response = await client.post(
            "/boards",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Minimal Board",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Board"
        # short_code should be auto-generated (5 uppercase alphanumeric chars)
        assert data["short_code"] is not None
        assert len(data["short_code"]) == 5
        # Verify defaults were applied
        assert data["icon"] == "fa-crown"  # Default icon
        assert data["unit"] is None  # Default unit (None)
        assert data["is_active"] is True  # Default active state
        assert data["sort_direction"] == "DESCENDING"  # Default sort direction
        assert data["keep_strategy"] == "ALL"  # Default keep strategy

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
                "game_id": "gam_00000000-0000-0000-0000-000000000000",
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
        assert "not found" in response.json()["error"].lower()

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

        logger.warning(response.json())

        assert response.status_code == 400
        assert "does not belong to account" in response.json()["error"].lower()

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
            "/boards/brd_00000000-0000-0000-0000-000000000000",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()

    async def test_list_boards_by_code(self, client: AsyncClient, db_session, test_api_key):
        """Test listing boards filtered by short code via API."""
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

        # Retrieve by short code using query parameter (must include account_id after refactor)
        response = await client.get(
            f"/boards?code=SR2025&account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == board_id
        assert data["data"][0]["short_code"] == "SR2025"

    async def test_list_boards_by_code_not_found(self, client: AsyncClient, test_api_key):
        """Test listing boards by non-existent short code returns empty list."""
        response = await client.get(
            "/boards?code=NONEXISTENT", headers={"leadr-api-key": test_api_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 0

    async def test_list_boards_by_account_and_code(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test listing boards filtered by both account_id and code."""
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

        # Create boards with different short codes for each account
        await client.post(
            "/boards",
            json={
                "account_id": str(account1.id),
                "game_id": str(game1.id),
                "name": "Account 1 Board",
                "icon": "star",
                "short_code": "CODE1",
                "unit": "points",
                "is_active": True,
                "sort_direction": "DESCENDING",
                "keep_strategy": "ALL",
            },
            headers={"leadr-api-key": test_api_key},
        )
        board2_response = await client.post(
            "/boards",
            json={
                "account_id": str(account2.id),
                "game_id": str(game2.id),
                "name": "Account 2 Board",
                "icon": "trophy",
                "short_code": "CODE2",
                "unit": "seconds",
                "is_active": True,
                "sort_direction": "ASCENDING",
                "keep_strategy": "BEST_ONLY",
            },
            headers={"leadr-api-key": test_api_key},
        )
        board2_id = board2_response.json()["id"]

        # List boards filtering by both account2 and CODE2
        response = await client.get(
            f"/boards?account_id={account2.id}&code=CODE2",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == board2_id
        assert data["data"][0]["name"] == "Account 2 Board"

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
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 2
        names = {b["name"] for b in data["data"]}
        assert "Board One" in names
        assert "Board Two" in names

    async def test_list_boards_requires_account_id_or_code(self, client: AsyncClient, test_api_key):
        """Test that listing boards defaults to authenticated user's account."""
        response = await client.get("/boards", headers={"leadr-api-key": test_api_key})

        # After refactor, account_id defaults to auth.account_id instead of requiring explicit param
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

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
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Account 1 Board"

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
            "/boards/brd_00000000-0000-0000-0000-000000000000",
            json={"name": "New Name"},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()

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
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Board Two"

    async def test_create_board_with_custom_slug(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a board with a custom slug."""
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

        # Create board with custom slug
        response = await client.post(
            "/boards",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Speed Run Board",
                "slug": "custom-speedrun-slug",
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
        assert data["slug"] == "custom-speedrun-slug"
        assert data["name"] == "Speed Run Board"

    async def test_create_board_auto_generates_slug_when_not_provided(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that slug is auto-generated from name when not provided."""
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

        # Create board without slug
        response = await client.post(
            "/boards",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "My Awesome Board",
                "icon": "trophy",
                "short_code": "MAB2025",
                "unit": "points",
                "is_active": True,
                "sort_direction": "DESCENDING",
                "keep_strategy": "ALL",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        # Should be auto-generated from "My Awesome Board" -> "my-awesome-board"
        assert data["slug"] == "my-awesome-board"
        assert data["name"] == "My Awesome Board"

    async def test_create_board_with_invalid_slug_format(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a board with invalid slug format returns 400."""
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

        # Try to create board with invalid slug (uppercase, special chars)
        response = await client.post(
            "/boards",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Invalid Slug Board",
                "slug": "Invalid_Slug!",
                "icon": "trophy",
                "short_code": "ISB2025",
                "unit": "points",
                "is_active": True,
                "sort_direction": "DESCENDING",
                "keep_strategy": "ALL",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400
        error_msg = response.json()["error"].lower()
        assert "slug" in error_msg

    async def test_create_board_with_duplicate_slug_fails(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating boards with duplicate slug in same account+game fails."""
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

        # Create first board with slug
        response1 = await client.post(
            "/boards",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "First Board",
                "slug": "my-unique-slug",
                "icon": "trophy",
                "short_code": "FIRST",
                "unit": "points",
                "is_active": True,
                "sort_direction": "DESCENDING",
                "keep_strategy": "ALL",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response1.status_code == 201

        # Try to create second board with same slug (should fail)
        response2 = await client.post(
            "/boards",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Second Board",
                "slug": "my-unique-slug",
                "icon": "star",
                "short_code": "SECOND",
                "unit": "points",
                "is_active": True,
                "sort_direction": "DESCENDING",
                "keep_strategy": "ALL",
            },
            headers={"leadr-api-key": test_api_key},
        )

        # Should fail due to unique constraint
        assert response2.status_code == 400

    async def test_superadmin_list_boards_without_account_id_returns_all(
        self, authenticated_client: AsyncClient, db_session
    ):
        """Test that superadmin can list boards WITHOUT account_id and sees all accounts."""
        from datetime import UTC, datetime

        from leadr.accounts.domain.account import Account, AccountStatus
        from leadr.accounts.services.repositories import AccountRepository
        from leadr.boards.services.board_service import BoardService
        from leadr.common.domain.ids import AccountID

        # Create two accounts with boards in each
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(),
            name="Account One Boards",
            slug="account-one-boards",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(),
            name="Account Two Boards",
            slug="account-two-boards",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)
        await account_repo.create(account2)

        # Create games and boards for each account
        game_service = GameService(db_session)
        game1 = await game_service.create_game(
            account_id=account1.id,
            name="Game Board 1",
        )
        game2 = await game_service.create_game(
            account_id=account2.id,
            name="Game Board 2",
        )

        board_service = BoardService(db_session)
        await board_service.create_board(
            account_id=account1.id,
            game_id=game1.id,
            name="Board from Account 1",
            icon="trophy",
            short_code="BRD1A1",
            unit="points",
        )
        await board_service.create_board(
            account_id=account2.id,
            game_id=game2.id,
            name="Board from Account 2",
            icon="star",
            short_code="BRD2A2",
            unit="points",
        )

        # List boards WITHOUT account_id - should return boards from ALL accounts
        response = await authenticated_client.get("/boards")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

        # Should contain boards from both accounts
        board_names = {b["name"] for b in data["data"]}
        assert "Board from Account 1" in board_names
        assert "Board from Account 2" in board_names

    async def test_create_board_with_description(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a board with description via API."""
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

        response = await client.post(
            "/boards",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Speed Run Board",
                "icon": "trophy",
                "short_code": "SRDAPI",
                "unit": "seconds",
                "description": "Complete the level as fast as possible",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Speed Run Board"
        assert data["description"] == "Complete the level as fast as possible"

    async def test_update_board_description(self, client: AsyncClient, db_session, test_api_key):
        """Test updating a board's description via API."""
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
                "name": "Board to Update",
                "icon": "trophy",
                "short_code": "UPDDSC",
                "unit": "points",
            },
            headers={"leadr-api-key": test_api_key},
        )
        board_id = create_response.json()["id"]

        # Update description
        update_response = await client.patch(
            f"/boards/{board_id}",
            json={"description": "A brand new description"},
            headers={"leadr-api-key": test_api_key},
        )

        assert update_response.status_code == 200
        data = update_response.json()
        assert data["description"] == "A brand new description"

    async def test_board_description_defaults_to_none(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that description defaults to None when not provided via API."""
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

        response = await client.post(
            "/boards",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Simple Board",
                "icon": "star",
                "short_code": "SMPBRD",
                "unit": "points",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["description"] is None
