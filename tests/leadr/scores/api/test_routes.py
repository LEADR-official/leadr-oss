"""Tests for Score API routes."""

import pytest
from httpx import AsyncClient

from leadr.accounts.services.account_service import AccountService
from leadr.auth.services.device_service import DeviceService
from leadr.boards.domain.board import BoardType, KeepStrategy, SortDirection
from leadr.boards.services.board_service import BoardService
from leadr.games.services.game_service import GameService
from leadr.scores.services.score_service import ScoreService


@pytest.mark.asyncio
class TestScoreRoutes:
    """Test suite for Score API routes."""

    async def test_create_score(self, client: AsyncClient, db_session, test_api_key):
        """Test creating a score via API."""
        # Create supporting entities
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

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create score
        response = await client.post(
            "/scores",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "board_id": str(board.id),
                "device_id": str(device.id),
                "player_name": "SpeedRunner99",
                "value": 123.45,
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["player_name"] == "SpeedRunner99"
        assert data["value"] == 123.45
        assert data["account_id"] == str(account.id)
        assert data["game_id"] == str(game.id)
        assert data["board_id"] == str(board.id)
        assert data["device_id"] == str(device.id)
        assert "id" in data
        assert "created_at" in data

    async def test_create_score_with_optional_fields(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a score with optional fields via API."""
        # Create supporting entities
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

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create score with optional fields (geo fields auto-populated by middleware)
        response = await client.post(
            "/scores",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "board_id": str(board.id),
                "device_id": str(device.id),
                "player_name": "SpeedRunner99",
                "value": 123.45,
                "value_display": "2:03.45",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["value_display"] == "2:03.45"
        # Geo fields will be None in tests (no real IP/GeoIP service)
        assert data["timezone"] is None
        assert data["country"] is None
        assert data["city"] is None

    async def test_create_score_with_board_not_found(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a score with non-existent board returns 404."""
        # Create account, device, and game
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

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
        )

        # Try to create score with non-existent board
        response = await client.post(
            "/scores",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "board_id": "brd_00000000-0000-0000-0000-000000000000",
                "device_id": str(device.id),
                "player_name": "SpeedRunner99",
                "value": 123.45,
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()

    async def test_create_score_with_board_from_different_account(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a score with board from different account returns 400."""
        # Create two accounts
        account_service = AccountService(db_session)
        account1 = await account_service.create_account(
            name="Account 1",
            slug="account-1",
        )
        account2 = await account_service.create_account(
            name="Account 2",
            slug="account-2",
        )

        # Create games for both accounts
        game_service = GameService(db_session)
        game1 = await game_service.create_game(
            account_id=account1.id,
            name="Game 1",
        )
        game2 = await game_service.create_game(
            account_id=account2.id,
            name="Game 2",
        )

        # Create device for account1
        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game1.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
        )

        # Create board for account2
        board_service = BoardService(db_session)
        board2 = await board_service.create_board(
            account_id=account2.id,
            game_id=game2.id,
            name="Account 2 Board",
            icon="star",
            short_code="A2B1",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Try to create score for account1 with account2's board
        response = await client.post(
            "/scores",
            json={
                "account_id": str(account1.id),
                "game_id": str(game1.id),
                "board_id": str(board2.id),
                "device_id": str(device.id),
                "player_name": "SpeedRunner99",
                "value": 123.45,
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400
        assert "does not belong to account" in response.json()["error"].lower()

    async def test_create_score_with_mismatched_game_id(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test creating a score with mismatched game_id returns 400."""
        # Create account and games
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Create two games
        game_service = GameService(db_session)
        game1 = await game_service.create_game(
            account_id=account.id,
            name="Game 1",
        )
        game2 = await game_service.create_game(
            account_id=account.id,
            name="Game 2",
        )

        # Create device
        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game1.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
        )

        # Create board for game1
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game1.id,
            name="Game 1 Board",
            icon="trophy",
            short_code="G1B1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Try to create score with game2 (mismatched)
        response = await client.post(
            "/scores",
            json={
                "account_id": str(account.id),
                "game_id": str(game2.id),
                "board_id": str(board.id),
                "device_id": str(device.id),
                "player_name": "SpeedRunner99",
                "value": 123.45,
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400
        assert "does not match board" in response.json()["error"].lower()

    async def test_get_score(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a score by ID via API."""
        # Create supporting entities
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

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create score
        score_service = ScoreService(db_session)
        score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        # Get score
        response = await client.get(
            f"/scores/{score.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(score.id)
        assert data["player_name"] == "SpeedRunner99"

    async def test_get_score_not_found(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a non-existent score returns 404."""
        response = await client.get(
            "/scores/scr_00000000-0000-0000-0000-000000000000",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404

    async def test_list_scores(self, client: AsyncClient, db_session, test_api_key):
        """Test listing scores for an account via API."""
        # Create supporting entities
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

        device_service = DeviceService(db_session)
        device1, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
        )
        device2, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="adf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb1",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create multiple scores from different devices
        score_service = ScoreService(db_session)
        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device1.id,
            player_name="Player1",
            value=100.0,
        )
        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device2.id,
            player_name="Player2",
            value=200.0,
        )

        # List scores
        response = await client.get(
            f"/scores?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 2
        names = {s["player_name"] for s in data["data"]}
        assert "Player1" in names
        assert "Player2" in names

    async def test_list_scores_filters_by_board(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering scores by board_id via API."""
        # Create supporting entities
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

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
        )

        board_service = BoardService(db_session)
        board1 = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Board 1",
            icon="trophy",
            short_code="B1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )
        board2 = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Board 2",
            icon="star",
            short_code="B2",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create scores for both boards
        score_service = ScoreService(db_session)
        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board1.id,
            device_id=device.id,
            player_name="Board1Score",
            value=100.0,
        )
        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board2.id,
            device_id=device.id,
            player_name="Board2Score",
            value=200.0,
        )

        # Filter by board1
        response = await client.get(
            f"/scores?account_id={account.id}&board_id={board1.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["player_name"] == "Board1Score"

    async def test_update_score(self, client: AsyncClient, db_session, test_api_key):
        """Test updating a score via API."""
        # Create supporting entities
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

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create score
        score_service = ScoreService(db_session)
        score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        # Update score
        response = await client.patch(
            f"/scores/{score.id}",
            json={
                "player_name": "NewName",
                "value": 200.0,
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["player_name"] == "NewName"
        assert data["value"] == 200.0

    async def test_update_score_not_found(self, client: AsyncClient, db_session, test_api_key):
        """Test updating a non-existent score returns 404."""
        response = await client.patch(
            "/scores/scr_00000000-0000-0000-0000-000000000000",
            json={"player_name": "NewName"},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404

    async def test_soft_delete_score(self, client: AsyncClient, db_session, test_api_key):
        """Test soft-deleting a score via API."""
        # Create supporting entities
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

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create score
        score_service = ScoreService(db_session)
        score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="SpeedRunner99",
            value=123.45,
        )

        # Soft-delete score
        response = await client.patch(
            f"/scores/{score.id}",
            json={"deleted": True},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200

        # Verify it's not in list
        response = await client.get(
            f"/scores?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 0

    async def test_list_scores_excludes_deleted(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that list_scores excludes soft-deleted scores."""
        # Create supporting entities
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

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_RUNS,  # Use RUN_RUNS to keep both scores
            keep_strategy=KeepStrategy.NA,
        )

        # Create two scores - RUN_RUNS keeps all
        score_service = ScoreService(db_session)
        score1, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="Score1",
            value=100.0,
        )
        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="Score2",
            value=200.0,
        )

        # Soft-delete score1
        await score_service.soft_delete(score1.id)

        # List should only return score2
        response = await client.get(
            f"/scores?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["player_name"] == "Score2"

    async def test_create_score_admin_auth_includes_device_id(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that admin-authenticated score creation includes device_id in response."""
        # Create supporting entities
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

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create score with admin auth
        response = await client.post(
            "/scores",
            json={
                "account_id": str(account.id),
                "game_id": str(game.id),
                "board_id": str(board.id),
                "device_id": str(device.id),
                "player_name": "AdminPlayer",
                "value": 100.0,
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 201
        data = response.json()
        # Admin auth should include device_id in response
        assert "device_id" in data
        assert data["device_id"] == str(device.id)

    async def test_create_score_client_auth_excludes_device_id(
        self, client: AsyncClient, db_session
    ):
        """Test that client-authenticated score creation excludes device_id from response."""
        # Create supporting entities
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

        device_service = DeviceService(db_session)
        device, access_token, _, nonce_value = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Generate a fresh nonce for the mutation (nonces are single-use)
        nonce_response = await client.get(
            "/client/nonce",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        fresh_nonce = nonce_response.json()["nonce_value"]

        # Create score with client auth (no account_id, game_id, device_id needed)
        # Client routes are now under /client prefix after refactor
        response = await client.post(
            "/client/scores",
            json={
                "board_id": str(board.id),
                "player_name": "ClientPlayer",
                "value": 200.0,
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "leadr-client-nonce": fresh_nonce,
            },
        )

        assert response.status_code == 201
        data = response.json()
        # Client auth should NOT include device_id in response
        assert "device_id" not in data
        assert data["player_name"] == "ClientPlayer"

    async def test_list_scores_admin_auth_includes_device_id_and_geo_fields(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that admin-authenticated score listing includes device_id and geo fields."""
        # Create supporting entities
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

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create a score
        score_service = ScoreService(db_session)
        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="TestPlayer",
            value=100.0,
        )

        # List scores with admin auth
        response = await client.get(
            f"/scores?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        # Admin auth should include device_id and geo fields in response
        assert "device_id" in data["data"][0]
        assert data["data"][0]["device_id"] == str(device.id)
        assert "timezone" in data["data"][0]
        assert "country" in data["data"][0]
        assert "city" in data["data"][0]

    async def test_list_scores_client_auth_excludes_device_id_and_geo_fields(
        self, client: AsyncClient, db_session
    ):
        """Test that client-authenticated score listing excludes device_id and geo fields."""
        # Create supporting entities
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

        device_service = DeviceService(db_session)
        device, access_token, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create a score
        score_service = ScoreService(db_session)
        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="TestPlayer",
            value=100.0,
        )

        # List scores with client auth (use /client prefix after refactor)
        # Client API doesn't accept account_id parameter - it's auto-derived from device token
        response = await client.get(
            "/client/scores",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        # Client auth should NOT include device_id or geo fields in response
        assert "device_id" not in data["data"][0]
        assert "timezone" not in data["data"][0]
        assert "country" not in data["data"][0]
        assert "city" not in data["data"][0]
        assert data["data"][0]["player_name"] == "TestPlayer"

    async def test_superadmin_list_scores_without_account_id_returns_all(
        self, authenticated_client: AsyncClient, db_session
    ):
        """Test that superadmin can list scores WITHOUT account_id and sees all accounts."""
        from datetime import UTC, datetime

        from leadr.accounts.domain.account import Account, AccountStatus
        from leadr.accounts.services.repositories import AccountRepository
        from leadr.boards.domain.board import KeepStrategy, SortDirection
        from leadr.boards.services.board_service import BoardService
        from leadr.common.domain.ids import AccountID

        # Create two accounts with scores in each
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(),
            name="Account One Scores",
            slug="account-one-scores",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(),
            name="Account Two Scores",
            slug="account-two-scores",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)
        await account_repo.create(account2)

        # Create games, devices, boards and scores for each account
        game_service = GameService(db_session)
        game1 = await game_service.create_game(
            account_id=account1.id,
            name="Game Score 1",
        )
        game2 = await game_service.create_game(
            account_id=account2.id,
            name="Game Score 2",
        )

        device_service = DeviceService(db_session)
        hash1 = "eee93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfe0"
        hash2 = "fff93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbff0"
        device1, _, _, _ = await device_service.start_session(
            game_id=game1.id,
            client_fingerprint=hash1,
        )
        device2, _, _, _ = await device_service.start_session(
            game_id=game2.id,
            client_fingerprint=hash2,
        )

        board_service = BoardService(db_session)
        board1 = await board_service.create_board(
            account_id=account1.id,
            game_id=game1.id,
            name="Board Score 1",
            icon="trophy",
            short_code="BSC1A1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )
        board2 = await board_service.create_board(
            account_id=account2.id,
            game_id=game2.id,
            name="Board Score 2",
            icon="star",
            short_code="BSC2A2",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        score_service = ScoreService(db_session)
        await score_service.create_score(
            account_id=account1.id,
            game_id=game1.id,
            board_id=board1.id,
            device_id=device1.id,
            player_name="Player From Account 1",
            value=1000.0,
        )
        await score_service.create_score(
            account_id=account2.id,
            game_id=game2.id,
            board_id=board2.id,
            device_id=device2.id,
            player_name="Player From Account 2",
            value=2000.0,
        )

        # List scores WITHOUT account_id - should return scores from ALL accounts
        response = await authenticated_client.get("/scores")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

        # Should contain scores from both accounts
        player_names = {s["player_name"] for s in data["data"]}
        assert "Player From Account 1" in player_names
        assert "Player From Account 2" in player_names

    async def test_list_scores_client_filter_by_device_id(self, client: AsyncClient, db_session):
        """Test that client can filter scores by device_id."""
        # Create supporting entities
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

        device_service = DeviceService(db_session)
        # Create two devices for the same game
        device1, access_token1, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="aaa93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfa0",
        )
        device2, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="bbb93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2025",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create scores from both devices
        score_service = ScoreService(db_session)
        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device1.id,
            player_name="Device1Player",
            value=100.0,
        )
        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device2.id,
            player_name="Device2Player",
            value=200.0,
        )

        # List scores with device_id filter using device1's token
        response = await client.get(
            f"/client/scores?device_id={device1.id}",
            headers={"Authorization": f"Bearer {access_token1}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["player_name"] == "Device1Player"

    async def test_list_scores_client_no_device_id_returns_all(
        self, client: AsyncClient, db_session
    ):
        """Test that client without device_id filter returns all scores for the game."""
        # Create supporting entities
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

        device_service = DeviceService(db_session)
        # Create two devices for the same game
        device1, access_token1, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="ccc93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfc0",
        )
        device2, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="ddd93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfd0",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            short_code="TB2026",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create scores from both devices
        score_service = ScoreService(db_session)
        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device1.id,
            player_name="Device1Player",
            value=100.0,
        )
        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device2.id,
            player_name="Device2Player",
            value=200.0,
        )

        # List scores WITHOUT device_id filter - should return all scores
        response = await client.get(
            "/client/scores",
            headers={"Authorization": f"Bearer {access_token1}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        player_names = {s["player_name"] for s in data["data"]}
        assert "Device1Player" in player_names
        assert "Device2Player" in player_names
