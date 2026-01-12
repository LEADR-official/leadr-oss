"""Tests for score rank functionality."""

import pytest
from httpx import AsyncClient

from leadr.accounts.domain.account import Account
from leadr.auth.domain.device import Device
from leadr.boards.domain.board import Board, KeepStrategy, SortDirection
from leadr.boards.services.board_service import BoardService
from leadr.scores.services.score_service import ScoreService


@pytest.mark.asyncio
class TestScoreRankAdmin:
    """Test suite for rank computation in admin API responses."""

    async def test_list_scores_admin_with_board_includes_rank(
        self,
        authenticated_client: AsyncClient,
        db_session,
        test_account: Account,
        test_board: Board,
        test_device: Device,
    ) -> None:
        """Test that scores include rank when board_id is provided."""
        # Create 5 scores with different values
        score_service = ScoreService(db_session)
        values = [100, 300, 500, 200, 400]
        for i, value in enumerate(values):
            await score_service.create_score(
                account_id=test_account.id,
                game_id=test_board.game_id,
                board_id=test_board.id,
                device_id=test_device.id,
                player_name=f"Player{i}",
                value=float(value),
            )

        # Get scores with board_id filter (board has DESCENDING sort)
        response = await authenticated_client.get(
            f"/scores?account_id={test_account.id}&board_id={test_board.id}"
        )

        assert response.status_code == 200
        data = response.json()
        scores = data["data"]

        # Verify ranks are present and in correct order
        # DESCENDING: 500 (rank 1), 400 (rank 2), 300 (rank 3), 200 (rank 4), 100 (rank 5)
        assert len(scores) == 5
        for i, score in enumerate(scores):
            assert "rank" in score
            assert score["rank"] == i + 1

        # Verify values match expected order
        expected_values = [500, 400, 300, 200, 100]
        actual_values = [s["value"] for s in scores]
        assert actual_values == expected_values

    async def test_list_scores_admin_without_board_rank_is_null(
        self,
        authenticated_client: AsyncClient,
        db_session,
        test_account: Account,
        test_board: Board,
        test_device: Device,
    ) -> None:
        """Test that rank is null when board_id is not provided."""
        # Create a score
        score_service = ScoreService(db_session)
        await score_service.create_score(
            account_id=test_account.id,
            game_id=test_board.game_id,
            board_id=test_board.id,
            device_id=test_device.id,
            player_name="Player1",
            value=100.0,
        )

        # Get scores WITHOUT board_id filter
        response = await authenticated_client.get(f"/scores?account_id={test_account.id}")

        assert response.status_code == 200
        data = response.json()
        scores = data["data"]

        assert len(scores) == 1
        assert "rank" in scores[0]
        assert scores[0]["rank"] is None

    async def test_list_scores_admin_rank_respects_ascending_sort_direction(
        self,
        authenticated_client: AsyncClient,
        db_session,
        test_account: Account,
        test_game,
        test_device: Device,
    ) -> None:
        """Test rank with ASCENDING board (lower is better, e.g., race times)."""
        # Create a board with ASCENDING sort direction
        board_service = BoardService(db_session)
        asc_board = await board_service.create_board(
            account_id=test_account.id,
            game_id=test_game.id,
            name="Race Times Board",
            icon="timer",
            short_code="RACE01",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.ALL,
        )

        # Create scores (lower is better)
        score_service = ScoreService(db_session)
        values = [50, 30, 70, 20, 40]
        for i, value in enumerate(values):
            await score_service.create_score(
                account_id=test_account.id,
                game_id=test_game.id,
                board_id=asc_board.id,
                device_id=test_device.id,
                player_name=f"Racer{i}",
                value=float(value),
            )

        # Get scores
        response = await authenticated_client.get(
            f"/scores?account_id={test_account.id}&board_id={asc_board.id}"
        )

        assert response.status_code == 200
        data = response.json()
        scores = data["data"]

        # ASCENDING: 20 (rank 1), 30 (rank 2), 40 (rank 3), 50 (rank 4), 70 (rank 5)
        assert len(scores) == 5
        expected_values = [20, 30, 40, 50, 70]
        actual_values = [s["value"] for s in scores]
        assert actual_values == expected_values

        # Verify ranks
        for i, score in enumerate(scores):
            assert score["rank"] == i + 1

    async def test_list_scores_admin_rank_handles_ties(
        self,
        authenticated_client: AsyncClient,
        db_session,
        test_account: Account,
        test_board: Board,
        test_device: Device,
    ) -> None:
        """Test rank handles tied values by created_at (later submission wins for DESC boards)."""
        import asyncio

        score_service = ScoreService(db_session)

        # Create first score
        await score_service.create_score(
            account_id=test_account.id,
            game_id=test_board.game_id,
            board_id=test_board.id,
            device_id=test_device.id,
            player_name="First",
            value=100.0,
        )

        # Small delay to ensure different created_at
        await asyncio.sleep(0.01)

        # Create second score with same value
        await score_service.create_score(
            account_id=test_account.id,
            game_id=test_board.game_id,
            board_id=test_board.id,
            device_id=test_device.id,
            player_name="Second",
            value=100.0,
        )

        # Get scores
        response = await authenticated_client.get(
            f"/scores?account_id={test_account.id}&board_id={test_board.id}"
        )

        assert response.status_code == 200
        data = response.json()
        scores = data["data"]

        # Both have same value, "Second" was created later so ranks better
        # (tie-breaker is created_at DESC).
        # For DESCENDING boards: higher value is better, and for ties, later created_at wins
        assert len(scores) == 2
        assert scores[0]["rank"] == 1
        assert scores[1]["rank"] == 2

        # Later submission should rank better (created_at DESC)
        first_score = next(s for s in scores if s["player_name"] == "First")
        second_score = next(s for s in scores if s["player_name"] == "Second")
        assert second_score["rank"] < first_score["rank"]

    async def test_get_single_score_admin_includes_rank(
        self,
        authenticated_client: AsyncClient,
        db_session,
        test_account: Account,
        test_board: Board,
        test_device: Device,
    ) -> None:
        """Test that GET /scores/{id} returns rank using score's board_id."""
        # Create multiple scores
        score_service = ScoreService(db_session)
        scores_created = []
        for value in [100, 300, 200]:
            score, _ = await score_service.create_score(
                account_id=test_account.id,
                game_id=test_board.game_id,
                board_id=test_board.id,
                device_id=test_device.id,
                player_name=f"Player{value}",
                value=float(value),
            )
            scores_created.append(score)

        # Get the middle score (value=200, should be rank 2 in DESCENDING)
        middle_score = next(s for s in scores_created if s.value == 200)
        response = await authenticated_client.get(f"/scores/{middle_score.id}")

        assert response.status_code == 200
        data = response.json()
        assert "rank" in data
        assert data["rank"] == 2  # 300=rank1, 200=rank2, 100=rank3


@pytest.mark.asyncio
class TestScoreRankClient:
    """Test suite for rank computation in client API responses."""

    async def test_list_scores_client_with_board_includes_rank(
        self,
        client: AsyncClient,
        db_session,
        test_account: Account,
        test_board: Board,
        test_device: Device,
    ) -> None:
        """Test that client endpoint also returns ranks when board_id provided."""
        from leadr.auth.services.device_service import DeviceService

        # Start a device session to get access token (use same fingerprint as test_device)
        device_service = DeviceService(db_session)
        _, access_token, _, _ = await device_service.start_session(
            game_id=test_board.game_id,
            client_fingerprint=test_device.client_fingerprint,
        )

        # Create scores
        score_service = ScoreService(db_session)
        for value in [100, 300, 200]:
            await score_service.create_score(
                account_id=test_account.id,
                game_id=test_board.game_id,
                board_id=test_board.id,
                device_id=test_device.id,
                player_name=f"Player{value}",
                value=float(value),
            )

        # Get scores via client endpoint with board_id
        response = await client.get(
            f"/client/scores?board_id={test_board.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        scores = data["data"]

        # Verify ranks are present (DESCENDING: 300=1, 200=2, 100=3)
        assert len(scores) == 3
        for score in scores:
            assert "rank" in score
            assert score["rank"] is not None

        # Verify order and ranks
        assert scores[0]["value"] == 300
        assert scores[0]["rank"] == 1
        assert scores[1]["value"] == 200
        assert scores[1]["rank"] == 2
        assert scores[2]["value"] == 100
        assert scores[2]["rank"] == 3

    async def test_list_scores_client_without_board_rank_is_null(
        self,
        client: AsyncClient,
        db_session,
        test_account: Account,
        test_board: Board,
        test_device: Device,
    ) -> None:
        """Test that client endpoint returns null rank without board_id."""
        from leadr.auth.services.device_service import DeviceService

        # Start a device session (use same fingerprint as test_device)
        device_service = DeviceService(db_session)
        _, access_token, _, _ = await device_service.start_session(
            game_id=test_board.game_id,
            client_fingerprint=test_device.client_fingerprint,
        )

        # Create a score
        score_service = ScoreService(db_session)
        await score_service.create_score(
            account_id=test_account.id,
            game_id=test_board.game_id,
            board_id=test_board.id,
            device_id=test_device.id,
            player_name="Player1",
            value=100.0,
        )

        # Get scores via client endpoint WITHOUT board_id
        response = await client.get(
            "/client/scores",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        scores = data["data"]

        assert len(scores) == 1
        assert "rank" in scores[0]
        assert scores[0]["rank"] is None


@pytest.mark.asyncio
class TestScoreRankPagination:
    """Test suite for rank computation with pagination."""

    async def test_list_scores_rank_with_pagination(
        self,
        authenticated_client: AsyncClient,
        db_session,
        test_account: Account,
        test_board: Board,
        test_device: Device,
    ) -> None:
        """Test ranks are continuous across pages (page 2 starts at 11, not 1)."""
        # Create 25 scores
        score_service = ScoreService(db_session)
        for i in range(25):
            await score_service.create_score(
                account_id=test_account.id,
                game_id=test_board.game_id,
                board_id=test_board.id,
                device_id=test_device.id,
                player_name=f"Player{i}",
                value=float(1000 - i),  # DESCENDING: 1000, 999, 998, ...
            )

        # Get first page (limit=10)
        response = await authenticated_client.get(
            f"/scores?account_id={test_account.id}&board_id={test_board.id}&limit=10"
        )
        assert response.status_code == 200
        page1 = response.json()

        # First page should have ranks 1-10
        assert len(page1["data"]) == 10
        page1_ranks = [s["rank"] for s in page1["data"]]
        assert page1_ranks == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        # Get second page
        cursor = page1["pagination"]["next_cursor"]
        response = await authenticated_client.get(
            f"/scores?account_id={test_account.id}&board_id={test_board.id}&limit=10&cursor={cursor}"
        )
        assert response.status_code == 200
        page2 = response.json()

        # Second page should have ranks 11-20
        assert len(page2["data"]) == 10
        page2_ranks = [s["rank"] for s in page2["data"]]
        assert page2_ranks == [11, 12, 13, 14, 15, 16, 17, 18, 19, 20]

    async def test_list_scores_around_includes_correct_ranks(
        self,
        authenticated_client: AsyncClient,
        db_session,
        test_account: Account,
        test_board: Board,
        test_device: Device,
    ) -> None:
        """Test around_score_id returns correct global ranks."""
        # Create 11 scores
        score_service = ScoreService(db_session)
        created_scores = []
        for i in range(11):
            score, _ = await score_service.create_score(
                account_id=test_account.id,
                game_id=test_board.game_id,
                board_id=test_board.id,
                device_id=test_device.id,
                player_name=f"Player{i}",
                value=float(1000 - (i * 100)),  # 1000, 900, 800, ..., 0
            )
            created_scores.append(score)

        # Get the middle score (value=500, should be rank 6)
        middle_score = next(s for s in created_scores if s.value == 500)

        # Get scores around the middle score with limit=5
        response = await authenticated_client.get(
            f"/scores?account_id={test_account.id}&board_id={test_board.id}"
            f"&around_score_id={middle_score.id}&limit=5"
        )
        assert response.status_code == 200
        data = response.json()
        scores = data["data"]

        # Should have 5 scores centered around rank 6
        # With limit=5: 2 above, target, 2 below -> ranks 4, 5, 6, 7, 8
        assert len(scores) == 5

        # Verify the target score is included with correct rank
        target_in_results = next((s for s in scores if s["id"] == str(middle_score.id)), None)
        assert target_in_results is not None
        assert target_in_results["rank"] == 6

        # All scores should have proper global ranks
        for score in scores:
            assert score["rank"] is not None
            assert 4 <= score["rank"] <= 8


@pytest.mark.asyncio
class TestScoreRankExcludesDeleted:
    """Test that soft-deleted scores don't affect ranking."""

    async def test_deleted_scores_excluded_from_ranking(
        self,
        authenticated_client: AsyncClient,
        db_session,
        test_account: Account,
        test_board: Board,
        test_device: Device,
    ) -> None:
        """Test soft-deleted scores are excluded from rank calculation."""
        score_service = ScoreService(db_session)

        # Create 3 scores: 300, 200, 100
        scores_created = []
        for value in [300, 200, 100]:
            score, _ = await score_service.create_score(
                account_id=test_account.id,
                game_id=test_board.game_id,
                board_id=test_board.id,
                device_id=test_device.id,
                player_name=f"Player{value}",
                value=float(value),
            )
            scores_created.append(score)

        # Soft-delete the top score (300)
        top_score = next(s for s in scores_created if s.value == 300)
        await score_service.soft_delete(top_score.id)

        # Get scores
        response = await authenticated_client.get(
            f"/scores?account_id={test_account.id}&board_id={test_board.id}"
        )

        assert response.status_code == 200
        data = response.json()
        scores = data["data"]

        # Should only have 2 scores, with ranks 1 and 2
        assert len(scores) == 2
        assert scores[0]["value"] == 200
        assert scores[0]["rank"] == 1  # Was rank 2, now rank 1
        assert scores[1]["value"] == 100
        assert scores[1]["rank"] == 2  # Was rank 3, now rank 2
