"""Tests for Score Flag API routes."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from leadr.accounts.services.account_service import AccountService
from leadr.auth.services.device_service import DeviceService
from leadr.boards.domain.board import KeepStrategy, SortDirection
from leadr.boards.services.board_service import BoardService
from leadr.games.services.game_service import GameService
from leadr.scores.domain.anti_cheat.enums import (
    FlagConfidence,
    FlagType,
    ScoreFlagStatus,
)
from leadr.scores.domain.anti_cheat.models import ScoreFlag
from leadr.scores.services.anti_cheat_repositories import ScoreFlagRepository
from leadr.scores.services.score_service import ScoreService


@pytest.mark.asyncio
class TestScoreFlagRoutes:
    """Test suite for Score Flag API routes."""

    async def test_list_flags(self, client: AsyncClient, db_session, test_api_key):
        """Test listing score flags via API."""
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
            device_id="test-device-001",
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
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create scores
        score_service = ScoreService(db_session)
        score1, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="Player1",
            value=100.0,
        )
        score2, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="Player2",
            value=200.0,
        )

        # Create flags for the scores
        flag_repo = ScoreFlagRepository(db_session)
        flag1 = ScoreFlag(
            score_id=score1.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.MEDIUM,
            metadata={"reason": "score improved too quickly"},
            status=ScoreFlagStatus.PENDING,
        )
        flag2 = ScoreFlag(
            score_id=score2.id,
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "duplicate submission detected"},
            status=ScoreFlagStatus.PENDING,
        )
        await flag_repo.create(flag1)
        await flag_repo.create(flag2)

        # List flags
        response = await client.get(
            f"/score-flags?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        flag_types = {f["flag_type"] for f in data}
        assert "VELOCITY" in flag_types
        assert "DUPLICATE" in flag_types

    async def test_list_flags_filter_by_board(self, client: AsyncClient, db_session, test_api_key):
        """Test filtering flags by board_id via API."""
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
            device_id="test-device-001",
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
            keep_strategy=KeepStrategy.BEST_ONLY,
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
            keep_strategy=KeepStrategy.ALL,
        )

        # Create scores for both boards
        score_service = ScoreService(db_session)
        score1, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board1.id,
            device_id=device.id,
            player_name="Board1Player",
            value=100.0,
        )
        score2, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board2.id,
            device_id=device.id,
            player_name="Board2Player",
            value=200.0,
        )

        # Create flags for both scores
        flag_repo = ScoreFlagRepository(db_session)
        flag1 = ScoreFlag(
            score_id=score1.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.MEDIUM,
            metadata={"board": "board1"},
            status=ScoreFlagStatus.PENDING,
        )
        flag2 = ScoreFlag(
            score_id=score2.id,
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.HIGH,
            metadata={"board": "board2"},
            status=ScoreFlagStatus.PENDING,
        )
        await flag_repo.create(flag1)
        await flag_repo.create(flag2)

        # Filter by board1
        response = await client.get(
            f"/score-flags?account_id={account.id}&board_id={board1.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["flag_type"] == "VELOCITY"

    async def test_list_flags_filter_by_status(self, client: AsyncClient, db_session, test_api_key):
        """Test filtering flags by status via API."""
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
            device_id="test-device-001",
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
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create scores
        score_service = ScoreService(db_session)
        score1, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="Player1",
            value=100.0,
        )
        score2, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="Player2",
            value=200.0,
        )

        # Create flags with different statuses
        flag_repo = ScoreFlagRepository(db_session)
        flag1 = ScoreFlag(
            score_id=score1.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.MEDIUM,
            metadata={},
            status=ScoreFlagStatus.PENDING,
        )
        flag2 = ScoreFlag(
            score_id=score2.id,
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.HIGH,
            metadata={},
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
        )
        await flag_repo.create(flag1)
        await flag_repo.create(flag2)

        # Filter by PENDING status
        response = await client.get(
            f"/score-flags?account_id={account.id}&status=PENDING",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "PENDING"
        assert data[0]["flag_type"] == "VELOCITY"

    async def test_list_flags_filter_by_flag_type(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test filtering flags by flag_type via API."""
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
            device_id="test-device-001",
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
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create scores
        score_service = ScoreService(db_session)
        score1, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="Player1",
            value=100.0,
        )
        score2, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="Player2",
            value=200.0,
        )

        # Create flags with different types
        flag_repo = ScoreFlagRepository(db_session)
        flag1 = ScoreFlag(
            score_id=score1.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.MEDIUM,
            metadata={},
            status=ScoreFlagStatus.PENDING,
        )
        flag2 = ScoreFlag(
            score_id=score2.id,
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.HIGH,
            metadata={},
            status=ScoreFlagStatus.PENDING,
        )
        await flag_repo.create(flag1)
        await flag_repo.create(flag2)

        # Filter by VELOCITY type
        response = await client.get(
            f"/score-flags?account_id={account.id}&flag_type=VELOCITY",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["flag_type"] == "VELOCITY"

    async def test_get_flag(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a single score flag by ID via API."""
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
            device_id="test-device-001",
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
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create score
        score_service = ScoreService(db_session)
        score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="Player1",
            value=100.0,
        )

        # Create flag
        flag_repo = ScoreFlagRepository(db_session)
        flag = ScoreFlag(
            score_id=score.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.MEDIUM,
            metadata={"reason": "score improved too quickly"},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_repo.create(flag)

        # Get flag
        response = await client.get(
            f"/score-flags/{created_flag.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(created_flag.id)
        assert data["flag_type"] == "VELOCITY"
        assert data["confidence"] == "MEDIUM"
        assert data["status"] == "PENDING"
        assert data["metadata"]["reason"] == "score improved too quickly"

    async def test_get_flag_not_found(self, client: AsyncClient, db_session, test_api_key):
        """Test getting a non-existent flag returns 404."""
        response = await client.get(
            "/score-flags/00000000-0000-0000-0000-000000000000",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 404

    async def test_review_flag(self, client: AsyncClient, db_session, test_api_key):
        """Test reviewing a score flag via API."""
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
            device_id="test-device-001",
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
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create score
        score_service = ScoreService(db_session)
        score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="Player1",
            value=100.0,
        )

        # Create flag
        flag_repo = ScoreFlagRepository(db_session)
        flag = ScoreFlag(
            score_id=score.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.MEDIUM,
            metadata={"reason": "score improved too quickly"},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_repo.create(flag)

        # Review flag - mark as confirmed cheat
        response = await client.patch(
            f"/score-flags/{created_flag.id}",
            json={
                "status": "CONFIRMED_CHEAT",
                "reviewer_decision": "Verified cheating behavior",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "CONFIRMED_CHEAT"
        assert data["reviewer_decision"] == "Verified cheating behavior"
        assert data["reviewed_at"] is not None

    async def test_review_flag_as_false_positive(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test marking a flag as false positive via API."""
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
            device_id="test-device-001",
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
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create score
        score_service = ScoreService(db_session)
        score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="Player1",
            value=100.0,
        )

        # Create flag
        flag_repo = ScoreFlagRepository(db_session)
        flag = ScoreFlag(
            score_id=score.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.MEDIUM,
            metadata={"reason": "score improved too quickly"},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_repo.create(flag)

        # Review flag - mark as false positive
        response = await client.patch(
            f"/score-flags/{created_flag.id}",
            json={
                "status": "FALSE_POSITIVE",
                "reviewer_decision": "Legitimate gameplay",
            },
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "FALSE_POSITIVE"
        assert data["reviewer_decision"] == "Legitimate gameplay"

    async def test_soft_delete_flag(self, client: AsyncClient, db_session, test_api_key):
        """Test soft-deleting a score flag via API."""
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
            device_id="test-device-001",
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
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create score
        score_service = ScoreService(db_session)
        score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="Player1",
            value=100.0,
        )

        # Create flag
        flag_repo = ScoreFlagRepository(db_session)
        flag = ScoreFlag(
            score_id=score.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.MEDIUM,
            metadata={},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_repo.create(flag)

        # Soft-delete flag
        response = await client.patch(
            f"/score-flags/{created_flag.id}",
            json={"deleted": True},
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200

        # Verify it's not in list
        response = await client.get(
            f"/score-flags?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        assert len(response.json()) == 0

    async def test_list_flags_excludes_deleted(self, client: AsyncClient, db_session, test_api_key):
        """Test that list_flags excludes soft-deleted flags."""
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
            device_id="test-device-001",
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
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Create score
        score_service = ScoreService(db_session)
        score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="Player1",
            value=100.0,
        )

        # Create two flags
        flag_repo = ScoreFlagRepository(db_session)
        flag1 = ScoreFlag(
            score_id=score.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.MEDIUM,
            metadata={},
            status=ScoreFlagStatus.PENDING,
        )
        flag2 = ScoreFlag(
            score_id=score.id,
            flag_type=FlagType.DUPLICATE,
            confidence=FlagConfidence.HIGH,
            metadata={},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag1 = await flag_repo.create(flag1)
        await flag_repo.create(flag2)

        # Soft-delete flag1 directly via repository
        flag1_entity = await flag_repo.get_by_id(created_flag1.id)
        assert flag1_entity is not None
        flag1_entity.deleted_at = datetime.now(UTC)
        await flag_repo.update(flag1_entity)

        # List should only return flag2
        response = await client.get(
            f"/score-flags?account_id={account.id}",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["flag_type"] == "DUPLICATE"

    async def test_list_flags_requires_account_id(
        self, client: AsyncClient, db_session, test_api_key
    ):
        """Test that listing flags requires account_id parameter."""
        response = await client.get(
            "/score-flags",
            headers={"leadr-api-key": test_api_key},
        )

        assert response.status_code == 400
        assert "account_id" in response.json()["detail"].lower()
