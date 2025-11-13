"""Tests for Score Submission Metadata API routes."""

import pytest
from httpx import AsyncClient

from leadr.accounts.services.account_service import AccountService
from leadr.auth.services.device_service import DeviceService
from leadr.boards.domain.board import KeepStrategy, SortDirection
from leadr.boards.services.board_service import BoardService
from leadr.games.services.game_service import GameService
from leadr.scores.services.score_service import ScoreService


@pytest.mark.asyncio
class TestScoreSubmissionMetaRoutes:
    """Test suite for Score Submission Metadata API routes."""

    async def test_list_submission_meta(self, client: AsyncClient, db_session, test_api_key):
        """Test listing score submission metadata via API."""
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

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create device and score submission
        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
        )

        # Submit a score to create submission metadata
        score_service = ScoreService(db_session)
        score, anti_cheat_result = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="Test Player",
            value=100.0,
        )
        await score_service.update_submission_metadata(
            saved_score=score,
            device_id=device.id,
            board_id=board.id,
            anti_cheat_result=anti_cheat_result,
        )

        # List submission metadata
        response = await client.get(
            f"/score-submission-metadata?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["device_id"] == str(device.id)
        assert data[0]["board_id"] == str(board.id)
        assert data[0]["submission_count"] == 1

    async def test_list_submission_meta_filter_by_board(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering submission metadata by board_id via API."""
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

        board_service = BoardService(db_session)
        board1 = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board 1",
            icon="trophy",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )
        board2 = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board 2",
            icon="trophy",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create device
        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
        )

        # Submit scores to both boards
        score_service = ScoreService(db_session)
        score1, result1 = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board1.id,
            device_id=device.id,
            player_name="Test Player",
            value=100.0,
        )
        await score_service.update_submission_metadata(
            saved_score=score1,
            device_id=device.id,
            board_id=board1.id,
            anti_cheat_result=result1,
        )
        score2, result2 = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board2.id,
            device_id=device.id,
            player_name="Test Player",
            value=200.0,
        )
        await score_service.update_submission_metadata(
            saved_score=score2,
            device_id=device.id,
            board_id=board2.id,
            anti_cheat_result=result2,
        )

        # Filter by board1
        response = await client.get(
            f"/score-submission-metadata?account_id={account.id}&board_id={board1.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["board_id"] == str(board1.id)

    async def test_list_submission_meta_filter_by_device(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering submission metadata by device_id via API."""
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

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create two devices
        device_service = DeviceService(db_session)
        device1, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
        )
        device2, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-002",
        )

        # Submit scores from both devices
        score_service = ScoreService(db_session)
        score1, result1 = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device1.id,
            player_name="Test Player",
            value=100.0,
        )
        await score_service.update_submission_metadata(
            saved_score=score1,
            device_id=device1.id,
            board_id=board.id,
            anti_cheat_result=result1,
        )
        score2, result2 = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device2.id,
            player_name="Test Player",
            value=200.0,
        )
        await score_service.update_submission_metadata(
            saved_score=score2,
            device_id=device2.id,
            board_id=board.id,
            anti_cheat_result=result2,
        )

        # Filter by device1
        response = await client.get(
            (f"/score-submission-metadata?account_id={account.id}&device_id={device1.id}"),
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["device_id"] == str(device1.id)

    async def test_get_submission_meta(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a single submission metadata by ID via API."""
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

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            icon="trophy",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create device and submit score
        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
        )

        score_service = ScoreService(db_session)
        score, anti_cheat_result = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="Test Player",
            value=100.0,
        )
        await score_service.update_submission_metadata(
            saved_score=score,
            device_id=device.id,
            board_id=board.id,
            anti_cheat_result=anti_cheat_result,
        )

        # Get submission metadata by device and board
        from leadr.scores.services.anti_cheat_repositories import (
            ScoreSubmissionMetaRepository,
        )

        meta_repo = ScoreSubmissionMetaRepository(db_session)
        meta = await meta_repo.get_by_device_and_board(device.id, board.id)
        assert meta is not None

        # Get via API
        response = await client.get(
            f"/score-submission-metadata/{meta.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(meta.id)
        assert data["device_id"] == str(device.id)
        assert data["board_id"] == str(board.id)
        assert data["submission_count"] == 1

    async def test_get_submission_meta_not_found(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test getting a non-existent submission metadata returns 404."""
        response = await client.get(
            "/score-submission-metadata/00000000-0000-0000-0000-000000000000",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404

    async def test_list_submission_meta_requires_account_id(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that listing submission metadata requires account_id parameter."""
        response = await client.get(
            "/score-submission-metadata",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400
        assert "account_id" in response.json()["detail"].lower()
