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
            keep_strategy=KeepStrategy.ALL,
        )

        # Create device and score submission
        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) >= 1
        assert data["data"][0]["device_id"] == str(device.id)
        assert data["data"][0]["board_id"] == str(board.id)
        assert data["data"][0]["submission_count"] == 1

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
            keep_strategy=KeepStrategy.ALL,
        )
        board2 = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board 2",
            icon="trophy",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
        )

        # Create device
        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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
        assert len(data["data"]) == 1
        assert data["data"][0]["board_id"] == str(board1.id)

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
            keep_strategy=KeepStrategy.ALL,
        )

        # Create two devices
        device_service = DeviceService(db_session)
        device1, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
        )
        device2, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="f0bfe8b352e3f87c10f5f37ccd2e3a5fb22ba397a54b43172a9770466537bc89",
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
            f"/score-submission-metadata?account_id={account.id}&device_id={device1.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["device_id"] == str(device1.id)

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
            keep_strategy=KeepStrategy.ALL,
        )

        # Create device and submit score
        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            client_fingerprint="cdf93498135a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbfb0",
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
            "/score-submission-metadata/sub_00000000-0000-0000-0000-000000000000",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404

    async def test_superadmin_list_submission_metadata_without_account_id_returns_all(
        self, authenticated_client: AsyncClient, db_session
    ):
        """Test that superadmin can list submission metadata WITHOUT account_id and sees all."""
        from datetime import UTC, datetime

        from leadr.accounts.domain.account import Account, AccountStatus
        from leadr.accounts.services.repositories import AccountRepository
        from leadr.common.domain.ids import AccountID

        # Create two accounts with submission metadata in each
        account_repo = AccountRepository(db_session)
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(),
            name="Account One Meta",
            slug="account-one-meta",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(),
            name="Account Two Meta",
            slug="account-two-meta",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)
        await account_repo.create(account2)

        # Create games, devices, boards, and scores for each account
        game_service = GameService(db_session)
        game1 = await game_service.create_game(
            account_id=account1.id,
            name="Game Meta 1",
        )
        game2 = await game_service.create_game(
            account_id=account2.id,
            name="Game Meta 2",
        )

        board_service = BoardService(db_session)
        board1 = await board_service.create_board(
            account_id=account1.id,
            game_id=game1.id,
            name="Board Meta 1",
            icon="trophy",
            short_code="BMT1A1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
        )
        board2 = await board_service.create_board(
            account_id=account2.id,
            game_id=game2.id,
            name="Board Meta 2",
            icon="star",
            short_code="BMT2A2",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
        )

        device_service = DeviceService(db_session)
        hash1 = "333934981c5a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbf30"
        hash2 = "444934981c5a6f1cba7de719278b27b7dd993547eec4127492fc94c35e3fbf40"
        device1, _, _, _ = await device_service.start_session(
            game_id=game1.id,
            client_fingerprint=hash1,
        )
        device2, _, _, _ = await device_service.start_session(
            game_id=game2.id,
            client_fingerprint=hash2,
        )

        # Create scores and update submission metadata for each account
        score_service = ScoreService(db_session)
        score1, result1 = await score_service.create_score(
            account_id=account1.id,
            game_id=game1.id,
            board_id=board1.id,
            device_id=device1.id,
            player_name="Player Meta 1",
            value=1000.0,
        )
        await score_service.update_submission_metadata(
            saved_score=score1,
            device_id=device1.id,
            board_id=board1.id,
            anti_cheat_result=result1,
        )
        score2, result2 = await score_service.create_score(
            account_id=account2.id,
            game_id=game2.id,
            board_id=board2.id,
            device_id=device2.id,
            player_name="Player Meta 2",
            value=2000.0,
        )
        await score_service.update_submission_metadata(
            saved_score=score2,
            device_id=device2.id,
            board_id=board2.id,
            anti_cheat_result=result2,
        )

        # List submission metadata WITHOUT account_id - should return from ALL accounts
        response = await authenticated_client.get("/score-submission-metadata")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

        # Should contain metadata from both accounts (at least 2 entries)
        device_ids = {m["device_id"] for m in data["data"]}
        assert str(device1.id) in device_ids
        assert str(device2.id) in device_ids
