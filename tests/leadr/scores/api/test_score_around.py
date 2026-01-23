"""Tests for around_score_id parameter on Score API routes."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from leadr.accounts.services.account_service import AccountService
from leadr.auth.services.device_service import DeviceService
from leadr.boards.domain.board import KeepStrategy, SortDirection
from leadr.boards.services.board_service import BoardService
from leadr.games.services.game_service import GameService
from leadr.scores.services.score_service import ScoreService


@pytest.mark.asyncio
class TestScoreAroundEndpoint:
    """Test suite for around_score_id parameter on list scores endpoints."""

    async def test_list_scores_around_score_id_admin(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test listing scores around a specific score via admin API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Around Test Account",
            slug="around-test-account",
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
            name="Around Test Board",
            icon="trophy",
            short_code="AROUND1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create 7 scores with different values
        score_service = ScoreService(db_session)
        scores = []
        for value in [100, 200, 300, 400, 500, 600, 700]:
            score, _ = await score_service.create_score(
                account_id=account.id,
                game_id=game.id,
                board_id=board.id,
                device_id=device.id,
                player_name=f"Player{value}",
                value=float(value),
            )
            scores.append(score)

        # Get scores centered around the score with value 400 (scores[3])
        target_score = scores[3]  # Player400
        response = await client.get(
            f"/scores?account_id={account.id}&board_id={board.id}"
            f"&around_score_id={target_score.id}&limit=5",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()

        # With DESC sort and limit=5:
        # Expected: [600, 500, 400, 300, 200] - 2 above, target, 2 below
        assert len(data["data"]) == 5
        values = [s["value"] for s in data["data"]]
        assert values == [600.0, 500.0, 400.0, 300.0, 200.0]

        # Verify pagination metadata
        assert data["pagination"]["count"] == 5
        assert data["pagination"]["has_prev"] is True  # More scores above
        assert data["pagination"]["has_next"] is True  # More scores below

    async def test_list_scores_around_score_id_at_top(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test around_score_id when target is at top of leaderboard."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Around Top Account",
            slug="around-top-account",
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
            name="Top Test Board",
            icon="trophy",
            short_code="TOP1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create 5 scores
        score_service = ScoreService(db_session)
        scores = []
        for value in [100, 200, 300, 400, 500]:
            score, _ = await score_service.create_score(
                account_id=account.id,
                game_id=game.id,
                board_id=board.id,
                device_id=device.id,
                player_name=f"Player{value}",
                value=float(value),
            )
            scores.append(score)

        # Target is highest score (value=500, top of DESC board)
        target_score = scores[4]  # Player500
        response = await client.get(
            f"/scores?account_id={account.id}&board_id={board.id}"
            f"&around_score_id={target_score.id}&limit=5",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()

        # Should get all 5 scores (target at top, fill below)
        assert len(data["data"]) == 5
        values = [s["value"] for s in data["data"]]
        assert values == [500.0, 400.0, 300.0, 200.0, 100.0]

        # No more above, no more below
        assert data["pagination"]["has_prev"] is False
        assert data["pagination"]["has_next"] is False

    async def test_list_scores_around_score_id_not_found(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test around_score_id with non-existent score returns 404."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Around 404 Account",
            slug="around-404-account",
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
            name="404 Test Board",
            icon="trophy",
            short_code="B404",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Use non-existent score ID
        non_existent_id = f"scr_{uuid4()}"
        response = await client.get(
            f"/scores?account_id={account.id}&board_id={board.id}"
            f"&around_score_id={non_existent_id}&limit=5",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()

    async def test_list_scores_around_cursor_mutual_exclusivity(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that around_score_id and cursor are mutually exclusive."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Mutual Exc Account",
            slug="mutual-exc-account",
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
            name="Mutual Exc Board",
            icon="trophy",
            short_code="MUTEXC",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
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

        # Try to use both cursor and around_score_id
        response = await client.get(
            f"/scores?account_id={account.id}&board_id={board.id}"
            f"&around_score_id={score.id}&cursor=somecursor&limit=5",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400
        error_msg = response.json()["error"].lower()
        assert "cursor" in error_msg or "around_score_id" in error_msg

    async def test_list_scores_around_requires_board_id(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that around_score_id requires board_id parameter."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="No Board Account",
            slug="no-board-account",
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
            name="No Board Test",
            icon="trophy",
            short_code="NOBRD",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
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

        # Try to use around_score_id without board_id
        response = await client.get(
            f"/scores?account_id={account.id}&around_score_id={score.id}&limit=5",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400
        error_msg = response.json()["error"].lower()
        assert "board_id" in error_msg

    async def test_list_scores_around_wrong_board(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test around_score_id with score from different board returns 400."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Wrong Board Account",
            slug="wrong-board-account",
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
        board1 = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Board 1",
            icon="trophy",
            short_code="BRD1",
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
            short_code="BRD2",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create score on board1
        score_service = ScoreService(db_session)
        score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board1.id,
            device_id=device.id,
            player_name="TestPlayer",
            value=100.0,
        )

        # Try to use around_score_id with board2
        response = await client.get(
            f"/scores?account_id={account.id}&board_id={board2.id}"
            f"&around_score_id={score.id}&limit=5",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400
        error_msg = response.json()["error"].lower()
        assert "board" in error_msg


@pytest.mark.asyncio
class TestScoreAroundClientEndpoint:
    """Test suite for around_score_id on client list scores endpoint."""

    async def test_list_scores_around_score_id_client(self, client: AsyncClient, db_session):
        """Test listing scores around a specific score via client API."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Client Around Account",
            slug="client-around-account",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        device_service = DeviceService(db_session)
        device, access_token, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Client Around Board",
            icon="trophy",
            short_code="CLIAROUND",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create 7 scores
        score_service = ScoreService(db_session)
        scores = []
        for value in [100, 200, 300, 400, 500, 600, 700]:
            score, _ = await score_service.create_score(
                account_id=account.id,
                game_id=game.id,
                board_id=board.id,
                device_id=device.id,
                player_name=f"Player{value}",
                value=float(value),
            )
            scores.append(score)

        # Get scores centered around the score with value 400
        target_score = scores[3]  # Player400
        response = await client.get(
            f"/client/scores?board_id={board.id}&around_score_id={target_score.id}&limit=5",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Expected: [600, 500, 400, 300, 200]
        assert len(data["data"]) == 5
        values = [s["value"] for s in data["data"]]
        assert values == [600.0, 500.0, 400.0, 300.0, 200.0]
