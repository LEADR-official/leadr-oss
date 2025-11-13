"""Tests for ScoreFlagService."""

from uuid import uuid4

import pytest

from leadr.accounts.services.account_service import AccountService
from leadr.auth.services.device_service import DeviceService
from leadr.boards.domain.board import KeepStrategy, SortDirection
from leadr.boards.services.board_service import BoardService
from leadr.common.domain.ids import ScoreFlagID
from leadr.games.services.game_service import GameService
from leadr.scores.domain.anti_cheat.enums import (
    FlagConfidence,
    FlagType,
    ScoreFlagStatus,
)
from leadr.scores.domain.anti_cheat.models import ScoreFlag
from leadr.scores.services.score_flag_service import ScoreFlagService
from leadr.scores.services.score_service import ScoreService


@pytest.mark.asyncio
class TestScoreFlagService:
    """Test suite for ScoreFlagService."""

    async def test_get_flag(self, db_session):
        """Test getting a flag by ID."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account",
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

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
        )

        # Create a score
        score_service = ScoreService(db_session)
        score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="Test Player",
            value=100.0,
        )

        # Create a flag
        flag = ScoreFlag(
            score_id=score.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        )

        service = ScoreFlagService(db_session)
        created_flag = await service.repository.create(flag)

        # Get the flag using get_flag method
        retrieved_flag = await service.get_flag(created_flag.id)

        assert retrieved_flag is not None
        assert retrieved_flag.id == created_flag.id
        assert retrieved_flag.score_id == score.id
        assert retrieved_flag.flag_type == FlagType.VELOCITY

    async def test_get_flag_returns_none_for_nonexistent(self, db_session):
        """Test get_flag returns None for nonexistent flag."""
        service = ScoreFlagService(db_session)
        flag = await service.get_flag(ScoreFlagID(uuid4()))

        assert flag is None

    async def test_update_flag_with_status_only(self, db_session):
        """Test updating a flag with status only."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account",
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

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
        )

        # Create a score
        score_service = ScoreService(db_session)
        score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="Test Player",
            value=100.0,
        )

        # Create a flag
        flag = ScoreFlag(
            score_id=score.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        )

        service = ScoreFlagService(db_session)
        created_flag = await service.repository.create(flag)

        # Update the flag status
        updated_flag = await service.update_flag(
            flag_id=created_flag.id,
            status=ScoreFlagStatus.FALSE_POSITIVE,
        )

        assert updated_flag.status == ScoreFlagStatus.FALSE_POSITIVE
        assert updated_flag.reviewed_at is not None
        assert updated_flag.reviewer_decision is None  # Not provided

    async def test_update_flag_with_reviewer_decision_only(self, db_session):
        """Test updating a flag with reviewer decision only."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account",
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

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
        )

        # Create a score
        score_service = ScoreService(db_session)
        score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="Test Player",
            value=100.0,
        )

        # Create a flag
        flag = ScoreFlag(
            score_id=score.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        )

        service = ScoreFlagService(db_session)
        created_flag = await service.repository.create(flag)

        # Update the flag with only reviewer decision
        updated_flag = await service.update_flag(
            flag_id=created_flag.id,
            reviewer_decision="Looks suspicious but needs more data",
        )

        assert updated_flag.reviewer_decision == "Looks suspicious but needs more data"
        assert updated_flag.status == ScoreFlagStatus.PENDING  # Unchanged
        assert updated_flag.reviewed_at is None  # Not set when status unchanged

    async def test_update_flag_with_both_status_and_decision(self, db_session):
        """Test updating a flag with both status and reviewer decision."""
        # Create supporting entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account",
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

        device_service = DeviceService(db_session)
        device, _, _, _ = await device_service.start_session(
            game_id=game.id,
            device_id="test-device-001",
        )

        # Create a score
        score_service = ScoreService(db_session)
        score, _ = await score_service.create_score(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            device_id=device.id,
            player_name="Test Player",
            value=100.0,
        )

        # Create a flag
        flag = ScoreFlag(
            score_id=score.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        )

        service = ScoreFlagService(db_session)
        created_flag = await service.repository.create(flag)

        # Update the flag with both status and decision
        updated_flag = await service.update_flag(
            flag_id=created_flag.id,
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
            reviewer_decision="Verified suspicious pattern",
        )

        assert updated_flag.status == ScoreFlagStatus.CONFIRMED_CHEAT
        assert updated_flag.reviewer_decision == "Verified suspicious pattern"
        assert updated_flag.reviewed_at is not None
