"""Tests for around_score_value parameter on Score API routes."""

from uuid import UUID

import pytest
from httpx import AsyncClient

from leadr.accounts.services.account_service import AccountService
from leadr.auth.services.device_service import DeviceService
from leadr.boards.domain.board import KeepStrategy, SortDirection
from leadr.boards.services.board_service import BoardService
from leadr.games.services.game_service import GameService
from leadr.scores.services.score_service import ScoreService

# Sentinel nil UUID for placeholder scores
NIL_UUID = UUID("00000000-0000-0000-0000-000000000000")
PLACEHOLDER_SCORE_ID = f"scr_{NIL_UUID}"
PLACEHOLDER_DEVICE_ID = f"dev_{NIL_UUID}"


@pytest.mark.asyncio
class TestScoreAroundValueEndpoint:
    """Test suite for around_score_value parameter on list scores endpoints."""

    async def test_list_scores_around_value_middle(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test around_score_value with value in middle of existing scores."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Around Value Test Account",
            slug="around-value-test-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Around Value Test Board",
            icon="trophy",
            short_code="AROUNDV1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
        )

        # Create 6 scores: 100, 200, 300, 500, 600, 700 (gap at 400)
        score_service = ScoreService(db_session)
        for value in [100, 200, 300, 500, 600, 700]:
            await score_service.create_score(
                account_id=account.id,
                game_id=game.id,
                board_id=board.id,
                device_id=device.id,
                player_name=f"Player{value}",
                value=float(value),
            )

        # Query with around_score_value=400 (between 300 and 500)
        response = await client.get(
            f"/scores?account_id={account.id}&board_id={board.id}&around_score_value=400&limit=5",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()

        # With DESC sort and limit=5:
        # Expected: [600, 500, placeholder(400), 300, 200]
        assert len(data["data"]) == 5
        values = [s["value"] for s in data["data"]]
        assert values == [600.0, 500.0, 400.0, 300.0, 200.0]

        # Verify placeholder is in the middle
        placeholder = data["data"][2]
        assert placeholder["value"] == 400.0
        assert placeholder["is_placeholder"] is True
        assert placeholder["id"] == PLACEHOLDER_SCORE_ID
        assert placeholder["rank"] == 4  # Rank 4 (after 700=1, 600=2, 500=3)

        # Verify non-placeholders have is_placeholder=False
        for i, score in enumerate(data["data"]):
            if i != 2:  # Skip the placeholder
                assert score["is_placeholder"] is False

    async def test_list_scores_around_value_at_top(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test around_score_value when value would be at top of leaderboard."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Around Value Top Account",
            slug="around-value-top-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Top Value Test Board",
            icon="trophy",
            short_code="TOPV1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
        )

        # Create 5 scores: 100, 200, 300, 400, 500
        score_service = ScoreService(db_session)
        for value in [100, 200, 300, 400, 500]:
            await score_service.create_score(
                account_id=account.id,
                game_id=game.id,
                board_id=board.id,
                device_id=device.id,
                player_name=f"Player{value}",
                value=float(value),
            )

        # Query with value=800 (better than all existing scores)
        response = await client.get(
            f"/scores?account_id={account.id}&board_id={board.id}&around_score_value=800&limit=5",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()

        # Placeholder should be at rank 1, followed by real scores
        assert len(data["data"]) == 5
        values = [s["value"] for s in data["data"]]
        assert values == [800.0, 500.0, 400.0, 300.0, 200.0]

        # Verify placeholder is first
        placeholder = data["data"][0]
        assert placeholder["is_placeholder"] is True
        assert placeholder["rank"] == 1

        assert data["pagination"]["has_prev"] is False
        assert data["pagination"]["has_next"] is True  # 100 is not shown

    async def test_list_scores_around_value_at_bottom(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test around_score_value when value would be at bottom of leaderboard."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Around Value Bottom Account",
            slug="around-value-bottom-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Bottom Value Test Board",
            icon="trophy",
            short_code="BOTV1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
        )

        # Create 5 scores: 100, 200, 300, 400, 500
        score_service = ScoreService(db_session)
        for value in [100, 200, 300, 400, 500]:
            await score_service.create_score(
                account_id=account.id,
                game_id=game.id,
                board_id=board.id,
                device_id=device.id,
                player_name=f"Player{value}",
                value=float(value),
            )

        # Query with value=50 (worse than all existing scores)
        response = await client.get(
            f"/scores?account_id={account.id}&board_id={board.id}&around_score_value=50&limit=5",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()

        # Placeholder should be at the end
        assert len(data["data"]) == 5
        values = [s["value"] for s in data["data"]]
        assert values == [400.0, 300.0, 200.0, 100.0, 50.0]

        # Verify placeholder is last
        placeholder = data["data"][4]
        assert placeholder["is_placeholder"] is True
        assert placeholder["rank"] == 6  # After all 5 existing scores

        assert data["pagination"]["has_prev"] is True  # 500 is not shown
        assert data["pagination"]["has_next"] is False

    async def test_list_scores_around_value_with_ties(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test around_score_value when value ties with existing scores."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Around Value Ties Account",
            slug="around-value-ties-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Ties Value Test Board",
            icon="trophy",
            short_code="TIESV1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
        )

        # Create scores with same value=300
        score_service = ScoreService(db_session)
        for i, value in enumerate([100, 300, 300, 300, 500]):
            await score_service.create_score(
                account_id=account.id,
                game_id=game.id,
                board_id=board.id,
                device_id=device.id,
                player_name=f"Player{i}",
                value=float(value),
            )

        # Query with same value=300 - placeholder should be at top of same-value group
        response = await client.get(
            f"/scores?account_id={account.id}&board_id={board.id}&around_score_value=300&limit=7",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()

        # With DESC sort, placeholder (newest) should be first among 300s
        # Expected order: [500, placeholder(300), 300, 300, 300, 100]
        assert len(data["data"]) == 6
        values = [s["value"] for s in data["data"]]
        assert values == [500.0, 300.0, 300.0, 300.0, 300.0, 100.0]

        # Placeholder should be the first 300 (rank 2, after 500)
        placeholder = data["data"][1]
        assert placeholder["is_placeholder"] is True
        assert placeholder["value"] == 300.0
        assert placeholder["rank"] == 2

    async def test_list_scores_around_value_placeholder_fields(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that placeholder score has correct sentinel values and fields."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Placeholder Fields Account",
            slug="placeholder-fields-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Placeholder Fields Board",
            icon="trophy",
            short_code="PLCFLD",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
        )

        # Create one score
        score_service = ScoreService(db_session)
        await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="ExistingPlayer",
            value=100.0,
        )

        # Query with around_score_value
        response = await client.get(
            f"/scores?account_id={account.id}&board_id={board.id}&around_score_value=200&limit=5",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()

        # Find the placeholder
        placeholder = next(s for s in data["data"] if s["is_placeholder"])

        # Verify sentinel values
        assert placeholder["id"] == PLACEHOLDER_SCORE_ID
        assert placeholder["device_id"] == PLACEHOLDER_DEVICE_ID
        assert placeholder["value"] == 200.0
        assert placeholder["player_name"] == ""
        assert placeholder["account_id"] == str(account.id)
        assert placeholder["game_id"] == str(game.id)
        assert placeholder["board_id"] == str(board.id)

        # Verify timestamps are present
        assert "created_at" in placeholder
        assert "updated_at" in placeholder

    async def test_list_scores_around_value_ascending_sort(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test around_score_value with ascending sort direction."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Around Value ASC Account",
            slug="around-value-asc-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="ASC Sort Board",
            icon="clock",
            short_code="ASCV1",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,  # Lower is better (like time)
            keep_strategy=KeepStrategy.ALL,
        )

        # Create scores: 10, 20, 30, 50, 60 (gap at 40)
        score_service = ScoreService(db_session)
        for value in [10, 20, 30, 50, 60]:
            await score_service.create_score(
                account_id=account.id,
                game_id=game.id,
                board_id=board.id,
                device_id=device.id,
                player_name=f"Player{value}",
                value=float(value),
            )

        # Query with around_score_value=40 (between 30 and 50)
        response = await client.get(
            f"/scores?account_id={account.id}&board_id={board.id}&around_score_value=40&limit=5",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()

        # With ASC sort (lower is better), limit=5:
        # Expected: [20, 30, placeholder(40), 50, 60]
        assert len(data["data"]) == 5
        values = [s["value"] for s in data["data"]]
        assert values == [20.0, 30.0, 40.0, 50.0, 60.0]

        # Verify placeholder
        placeholder = data["data"][2]
        assert placeholder["is_placeholder"] is True
        assert placeholder["rank"] == 4  # After 10, 20, 30

    async def test_list_scores_around_value_cursor_mutual_exclusivity(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that around_score_value and cursor are mutually exclusive."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Value Cursor Mutual Account",
            slug="value-cursor-mutual-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Mutual Exc Board",
            icon="trophy",
            short_code="VMUTEX",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
        )

        # Try to use both cursor and around_score_value
        response = await client.get(
            f"/scores?account_id={account.id}&board_id={board.id}"
            f"&around_score_value=100&cursor=somecursor&limit=5",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400
        error_msg = response.json()["error"].lower()
        assert "cursor" in error_msg or "around_score_value" in error_msg

    async def test_list_scores_around_value_around_id_mutual_exclusivity(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that around_score_value and around_score_id are mutually exclusive."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Value ID Mutual Account",
            slug="value-id-mutual-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Value ID Mutual Board",
            icon="trophy",
            short_code="VIDMUT",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
        )

        # Create a score
        score_service = ScoreService(db_session)
        score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="TestPlayer",
            value=100.0,
        )

        # Try to use both around_score_id and around_score_value
        response = await client.get(
            f"/scores?account_id={account.id}&board_id={board.id}"
            f"&around_score_id={score.id}&around_score_value=200&limit=5",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400
        error_msg = response.json()["error"].lower()
        assert "around_score_id" in error_msg or "around_score_value" in error_msg

    async def test_list_scores_around_value_requires_board_id(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that around_score_value requires board_id parameter."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Value No Board Account",
            slug="value-no-board-account",
        )

        # Try to use around_score_value without board_id
        response = await client.get(
            f"/scores?account_id={account.id}&around_score_value=100&limit=5",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400
        error_msg = response.json()["error"].lower()
        assert "board_id" in error_msg


@pytest.mark.asyncio
class TestScoreAroundValueClientEndpoint:
    """Test suite for around_score_value on client list scores endpoint."""

    async def test_list_scores_around_value_client(self, client: AsyncClient, db_session):
        """Test listing scores around a value via client API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Client Around Value Account",
            slug="client-around-value-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        device_service = DeviceService(db_session)
        device, access_token, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Client Around Value Board",
            icon="trophy",
            short_code="CLIAVB",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
        )

        # Create 6 scores
        score_service = ScoreService(db_session)
        for value in [100, 200, 300, 500, 600, 700]:
            await score_service.create_score(
                account_id=account.id,
                game_id=game.id,
                board_id=board.id,
                device_id=device.id,
                player_name=f"Player{value}",
                value=float(value),
            )

        # Query with around_score_value=400 via client API
        response = await client.get(
            f"/client/scores?board_id={board.id}&around_score_value=400&limit=5",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Expected: [600, 500, placeholder(400), 300, 200]
        assert len(data["data"]) == 5
        values = [s["value"] for s in data["data"]]
        assert values == [600.0, 500.0, 400.0, 300.0, 200.0]

        # Verify placeholder (client response doesn't have device_id)
        placeholder = data["data"][2]
        assert placeholder["is_placeholder"] is True
        assert placeholder["rank"] == 4  # Rank 4 (after 700=1, 600=2, 500=3)

    async def test_list_scores_around_value_client_empty_board(
        self, client: AsyncClient, db_session
    ):
        """Test around_score_value on empty board returns only placeholder."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Client Empty Board Account",
            slug="client-empty-board-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        device_service = DeviceService(db_session)
        _, access_token, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Empty Board",
            icon="trophy",
            short_code="EMPTY1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
        )

        # Query with around_score_value on empty board
        response = await client.get(
            f"/client/scores?board_id={board.id}&around_score_value=100&limit=5",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Should return only the placeholder
        assert len(data["data"]) == 1
        placeholder = data["data"][0]
        assert placeholder["is_placeholder"] is True
        assert placeholder["value"] == 100.0
        assert placeholder["rank"] == 1

        assert data["pagination"]["has_prev"] is False
        assert data["pagination"]["has_next"] is False
