"""Tests for Board API routes."""

import hashlib
from datetime import UTC, datetime, timedelta
from urllib.parse import quote
from uuid import uuid4

import pytest
from httpx import AsyncClient

from leadr.accounts.services.account_service import AccountService
from leadr.auth.domain.identity import IdentityKind
from leadr.auth.services.device_service import DeviceService
from leadr.auth.services.identity_service import IdentityService
from leadr.boards.domain.board import BoardType, KeepStrategy, SortDirection
from leadr.boards.services.board_service import BoardService
from leadr.games.services.game_service import GameService


@pytest.mark.asyncio
class TestBoardRoutes:
    """Test suite for Board API routes."""

    async def test_create_ratio_board_requires_config(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that RATIO boards require ratio_config."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-ratio-required",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        response = await client.post(
            "/boards",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Ratio Board",
                "sort_direction": "DESCENDING",
                "board_type": "RATIO",
                "keep_strategy": "NA",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400
        assert "ratio_config is required" in response.json()["error"]

    async def test_create_ratio_board_with_valid_config(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a RATIO board with valid ratio_config."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-ratio-valid",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        numerator_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Wins",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.COUNTER,
            keep_strategy=KeepStrategy.NA,
        )
        denominator_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Losses",
            sort_direction=SortDirection.ASCENDING,
            board_type=BoardType.COUNTER,
            keep_strategy=KeepStrategy.NA,
        )

        response = await client.post(
            "/boards",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Win Rate",
                "sort_direction": "DESCENDING",
                "board_type": "RATIO",
                "keep_strategy": "NA",
                "ratio_config": {
                    "numerator_board_id": str(numerator_board.id),
                    "denominator_board_id": str(denominator_board.id),
                    "zero_denominator_policy": "NULL",
                    "min_denominator": 10,
                    "min_numerator": 0,
                    "scale": 100,
                    "display": "PERCENT",
                    "decimals": 2,
                    "tie_breaker": "NUMERATOR_DESC_DENOMINATOR_ASC",
                },
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Win Rate"
        assert data["board_type"] == "RATIO"
        assert data["ratio_config"] is not None
        assert data["ratio_config"]["numerator_board_id"] == str(numerator_board.id)
        assert data["ratio_config"]["denominator_board_id"] == str(denominator_board.id)

    async def test_create_ratio_board_invalid_numerator(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating RATIO board with invalid numerator_board_id returns 400."""
        # Create account via API
        account_resp = await client.post(
            "/accounts",
            json={
                "name": "Test Account",
                "slug": "test-ratio-invalid-num",
            },
            headers={"leadr-api-key": test_api_key},
        )
        assert account_resp.status_code == 201
        account_id = account_resp.json()["id"]

        # Create game via API
        game_resp = await client.post(
            "/games",
            json={
                "account_id": account_id,
                "name": "Test Game",
            },
            headers={"leadr-api-key": test_api_key},
        )
        assert game_resp.status_code == 201
        game_id = game_resp.json()["id"]

        # Create denominator board via API
        denom_resp = await client.post(
            "/boards",
            json={
                "account_id": account_id,
                "game_id": game_id,
                "name": "Losses",
                "sort_direction": "ASCENDING",
                "board_type": "COUNTER",
                "keep_strategy": "NA",
            },
            headers={"leadr-api-key": test_api_key},
        )
        assert denom_resp.status_code == 201
        denominator_board_id = denom_resp.json()["id"]

        response = await client.post(
            "/boards",
            json={
                "account_id": account_id,
                "game_id": game_id,
                "name": "Win Rate",
                "sort_direction": "DESCENDING",
                "board_type": "RATIO",
                "keep_strategy": "NA",
                "ratio_config": {
                    "numerator_board_id": "brd_00000000-0000-0000-0000-000000000000",
                    "denominator_board_id": denominator_board_id,
                },
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400
        assert "Invalid numerator_board_id: board not found" in response.json()["error"]

    async def test_create_board_game_not_found(self, client: AsyncClient, db_session, test_api_key):
        """Test creating board with non-existent game."""
        # Create account via API
        account_resp = await client.post(
            "/accounts",
            json={
                "name": "Test Account",
                "slug": "test-board-game-notfound",
            },
            headers={"leadr-api-key": test_api_key},
        )
        assert account_resp.status_code == 201
        account_id = account_resp.json()["id"]

        response = await client.post(
            "/boards",
            json={
                "account_id": account_id,
                "game_id": "gam_00000000-0000-0000-0000-000000000000",
                "name": "Test Board",
                "sort_direction": "DESCENDING",
                "board_type": "RUN_IDENTITY",
                "keep_strategy": "BEST",
            },
            headers={"leadr-api-key": test_api_key},
        )

        # IntegrityError is caught and returned as 404
        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()

    async def test_get_board_by_id(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a board by ID."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-get-board",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="My Board",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        response = await client.get(
            f"/boards/{board.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(board.id)
        assert data["name"] == "My Board"

    async def test_get_ratio_board_includes_config(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test getting a RATIO board includes ratio_config."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-get-ratio",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        numerator_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Wins",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.COUNTER,
            keep_strategy=KeepStrategy.NA,
        )
        denominator_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Losses",
            sort_direction=SortDirection.ASCENDING,
            board_type=BoardType.COUNTER,
            keep_strategy=KeepStrategy.NA,
        )

        # Create RATIO board via API
        create_response = await client.post(
            "/boards",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Win Rate",
                "sort_direction": "DESCENDING",
                "board_type": "RATIO",
                "keep_strategy": "NA",
                "ratio_config": {
                    "numerator_board_id": str(numerator_board.id),
                    "denominator_board_id": str(denominator_board.id),
                },
            },
            headers={"leadr-api-key": test_api_key},
        )
        assert create_response.status_code == 201
        ratio_board_id = create_response.json()["id"]

        response = await client.get(
            f"/boards/{ratio_board_id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["board_type"] == "RATIO"
        assert data["ratio_config"] is not None

    async def test_get_board_not_found(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a non-existent board returns 404."""
        response = await client.get(
            "/boards/brd_00000000-0000-0000-0000-000000000000",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()

    async def test_list_boards_filter_by_game_slug(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering boards by game_slug."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-game-slug-filter",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id, name="Test Game", slug="test-game-slug-unique"
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="My Board",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        response = await client.get(
            "/boards?game_slug=test-game-slug-unique",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1
        board_ids = [b["id"] for b in data["data"]]
        assert str(board.id) in board_ids

    async def test_list_boards_game_slug_not_found(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering by non-existent game_slug returns 404."""
        response = await client.get(
            "/boards?game_slug=nonexistent-game-slug",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()

    async def test_list_boards_slug_requires_game_slug(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that board slug filter requires game_slug."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-slug-requires-game",
        )

        response = await client.get(
            f"/boards?slug=my-board&account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400
        assert "game_slug parameter is required" in response.json()["error"]

    async def test_list_boards_filter_by_slug_and_game_slug(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering boards by both game_slug and slug."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-slug-and-game",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id, name="Test Game", slug="slug-test-game"
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="My Board",
            slug="my-specific-board",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        response = await client.get(
            "/boards?game_slug=slug-test-game&slug=my-specific-board",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == str(board.id)
        assert data["data"][0]["slug"] == "my-specific-board"

    async def test_list_boards_filter_by_date_range(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering boards by date range."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-date-range",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        now = datetime.now(UTC)
        starts_at = now + timedelta(days=1)
        ends_at = now + timedelta(days=7)

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Seasonal Board",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
            starts_at=starts_at,
            ends_at=ends_at,
        )

        # Filter by starts_after and ends_before
        starts_after = quote(now.isoformat(), safe="")
        ends_before = quote((now + timedelta(days=10)).isoformat(), safe="")
        response = await client.get(
            f"/boards?account_id={account.id}"
            f"&starts_after={starts_after}"
            f"&ends_before={ends_before}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        board_ids = [b["id"] for b in data["data"]]
        assert str(board.id) in board_ids

    async def test_list_boards_filter_by_starts_before_ends_after(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering boards by starts_before and ends_after."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-date-range-2",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        now = datetime.now(UTC)
        starts_at = now + timedelta(days=1)
        ends_at = now + timedelta(days=30)

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Long Board",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
            starts_at=starts_at,
            ends_at=ends_at,
        )

        # Filter by starts_before and ends_after
        starts_before = quote((now + timedelta(days=5)).isoformat(), safe="")
        ends_after = quote((now + timedelta(days=20)).isoformat(), safe="")
        response = await client.get(
            f"/boards?account_id={account.id}"
            f"&starts_before={starts_before}"
            f"&ends_after={ends_after}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        board_ids = [b["id"] for b in data["data"]]
        assert str(board.id) in board_ids

    async def test_update_board(self, client: AsyncClient, db_session, test_api_key):
        """Test updating a board."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-update-board",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Original Name",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        response = await client.patch(
            f"/boards/{board.id}",
            json={"name": "Updated Name", "is_active": False},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["is_active"] is False

    async def test_update_board_soft_delete(self, client: AsyncClient, db_session, test_api_key):
        """Test soft deleting a board."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-soft-delete",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="To Delete",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        response = await client.patch(
            f"/boards/{board.id}",
            json={"deleted": True},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        # Verify the board was deleted by trying to get it
        get_response = await client.get(
            f"/boards/{board.id}",
            headers={"leadr-api-key": test_api_key},
        )
        # Soft-deleted boards should return 404
        assert get_response.status_code == 404

    async def test_update_ratio_board_config(self, client: AsyncClient, db_session, test_api_key):
        """Test updating a RATIO board's ratio_config."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-update-ratio",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        numerator_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Wins",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.COUNTER,
            keep_strategy=KeepStrategy.NA,
        )
        denominator_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Losses",
            sort_direction=SortDirection.ASCENDING,
            board_type=BoardType.COUNTER,
            keep_strategy=KeepStrategy.NA,
        )

        # Create RATIO board
        create_response = await client.post(
            "/boards",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Win Rate",
                "sort_direction": "DESCENDING",
                "board_type": "RATIO",
                "keep_strategy": "NA",
                "ratio_config": {
                    "numerator_board_id": str(numerator_board.id),
                    "denominator_board_id": str(denominator_board.id),
                    "min_denominator": 5,
                    "decimals": 1,
                },
            },
            headers={"leadr-api-key": test_api_key},
        )
        assert create_response.status_code == 201
        ratio_board_id = create_response.json()["id"]

        # Update ratio_config (need to provide all required fields for the request model)
        response = await client.patch(
            f"/boards/{ratio_board_id}",
            json={
                "ratio_config": {
                    "numerator_board_id": str(numerator_board.id),
                    "denominator_board_id": str(denominator_board.id),
                    "min_denominator": 10,
                    "decimals": 2,
                    "scale": 100,
                }
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ratio_config"]["min_denominator"] == 10
        assert data["ratio_config"]["decimals"] == 2

    async def test_update_board_not_found(self, client: AsyncClient, db_session, test_api_key):
        """Test updating a non-existent board returns 404."""
        response = await client.patch(
            "/boards/brd_00000000-0000-0000-0000-000000000000",
            json={"name": "New Name"},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()

    async def test_list_boards_filter_by_is_published(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering boards by is_published status."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-published-filter",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        # Create a published board
        _published_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Published Board",
            is_published=True,
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )
        # Create an unpublished board
        await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Unpublished Board",
            is_published=False,
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        response = await client.get(
            f"/boards?account_id={account.id}&is_published=true",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        # Should only get published boards
        for board in data["data"]:
            assert board["is_published"] is True

    async def test_update_ratio_board_without_config_change(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test updating a RATIO board without changing ratio_config."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-update-ratio-no-config",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        numerator_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Wins",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.COUNTER,
            keep_strategy=KeepStrategy.NA,
        )
        denominator_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Losses",
            sort_direction=SortDirection.ASCENDING,
            board_type=BoardType.COUNTER,
            keep_strategy=KeepStrategy.NA,
        )

        # Create RATIO board
        create_response = await client.post(
            "/boards",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "name": "Win Rate",
                "sort_direction": "DESCENDING",
                "board_type": "RATIO",
                "keep_strategy": "NA",
                "ratio_config": {
                    "numerator_board_id": str(numerator_board.id),
                    "denominator_board_id": str(denominator_board.id),
                },
            },
            headers={"leadr-api-key": test_api_key},
        )
        assert create_response.status_code == 201
        ratio_board_id = create_response.json()["id"]

        # Update only the name, not the ratio_config
        response = await client.patch(
            f"/boards/{ratio_board_id}",
            json={"name": "Updated Win Rate"},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Win Rate"
        # ratio_config should still be present
        assert data["ratio_config"] is not None


@pytest.mark.asyncio
class TestBoardClientRoutes:
    """Test suite for Board Client API routes."""

    async def test_list_boards_client(self, client: AsyncClient, db_session, test_api_key):
        """Test listing boards via Client API."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-client-boards",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_client_boards_1",
            display_name="TestPlayer",
        )

        # Create a device session via API
        fingerprint = hashlib.sha256(str(uuid4()).encode()).hexdigest()
        session_response = await client.post(
            "/client/sessions",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "display_name": "TestPlayer",
                "client_fingerprint": fingerprint,
            },
            headers={"leadr-api-key": test_api_key},
        )
        assert session_response.status_code == 201
        access_token = session_response.json()["access_token"]

        board_service = BoardService(db_session)
        _board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Active Board",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create an inactive board (should not appear for client)
        await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Inactive Board",
            is_active=False,
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        response = await client.get(
            "/client/boards",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        # Client should only see active boards
        board_names = [b["name"] for b in data["data"]]
        assert "Active Board" in board_names
        assert "Inactive Board" not in board_names

    async def test_list_boards_client_filter_by_game_slug(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test Client API boards filtered by game_slug."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-client-game-slug",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id, name="Client Game", slug="client-game-unique-slug"
        )

        # Create device session
        fingerprint = hashlib.sha256(str(uuid4()).encode()).hexdigest()
        session_response = await client.post(
            "/client/sessions",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "display_name": "TestPlayer",
                "client_fingerprint": fingerprint,
            },
            headers={"leadr-api-key": test_api_key},
        )
        assert session_response.status_code == 201
        access_token = session_response.json()["access_token"]

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Game Board",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        response = await client.get(
            "/client/boards?game_slug=client-game-unique-slug",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        board_ids = [b["id"] for b in data["data"]]
        assert str(board.id) in board_ids

    async def test_list_boards_client_date_filters(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test Client API boards with date filters."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-client-dates",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        # Create device session
        fingerprint = hashlib.sha256(str(uuid4()).encode()).hexdigest()
        session_response = await client.post(
            "/client/sessions",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "display_name": "TestPlayer",
                "client_fingerprint": fingerprint,
            },
            headers={"leadr-api-key": test_api_key},
        )
        assert session_response.status_code == 201
        access_token = session_response.json()["access_token"]

        now = datetime.now(UTC)
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Seasonal Board",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
            starts_at=now + timedelta(days=1),
            ends_at=now + timedelta(days=30),
        )

        starts_after = quote(now.isoformat(), safe="")
        ends_before = quote((now + timedelta(days=60)).isoformat(), safe="")
        response = await client.get(
            f"/client/boards?starts_after={starts_after}&ends_before={ends_before}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        board_ids = [b["id"] for b in data["data"]]
        assert str(board.id) in board_ids
