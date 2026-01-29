"""Tests for ScoreFlagService."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.services.account_service import AccountService
from leadr.auth.domain.identity import IdentityKind
from leadr.auth.services.device_service import DeviceService
from leadr.auth.services.identity_service import IdentityService
from leadr.boards.domain.board import BoardType, KeepStrategy, SortDirection
from leadr.boards.services.board_service import BoardService
from leadr.boards.services.board_state_service import BoardStateService
from leadr.boards.services.run_entry_service import RunEntryService
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import ScoreEventID, ScoreFlagID, UserID
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

    async def test_get_flag(self, db_session: AsyncSession, score_event_orm):
        """Test getting a flag by ID."""
        # Create a flag using the score_event fixture
        flag = ScoreFlag(
            score_event_id=ScoreEventID(score_event_orm.id),
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
        assert retrieved_flag.score_event_id == ScoreEventID(score_event_orm.id)
        assert retrieved_flag.flag_type == FlagType.VELOCITY

    async def test_get_flag_returns_none_for_nonexistent(self, db_session: AsyncSession):
        """Test get_flag returns None for nonexistent flag."""
        service = ScoreFlagService(db_session)
        flag = await service.get_flag(ScoreFlagID(uuid4()))

        assert flag is None

    async def test_update_flag_with_status_only(self, db_session: AsyncSession, score_event_orm):
        """Test updating a flag with status only."""
        # Create a flag using the score_event fixture
        flag = ScoreFlag(
            score_event_id=ScoreEventID(score_event_orm.id),
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

    async def test_update_flag_with_reviewer_decision_only(
        self, db_session: AsyncSession, score_event_orm
    ):
        """Test updating a flag with reviewer decision only."""
        # Create a flag using the score_event fixture
        flag = ScoreFlag(
            score_event_id=ScoreEventID(score_event_orm.id),
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

    async def test_update_flag_with_both_status_and_decision(
        self, db_session: AsyncSession, score_event_orm
    ):
        """Test updating a flag with both status and reviewer decision."""
        # Create a flag using the score_event fixture
        flag = ScoreFlag(
            score_event_id=ScoreEventID(score_event_orm.id),
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


@pytest.mark.asyncio
class TestRankingSyncForRunRuns:
    """Test suite for ranking sync with RUN_RUNS boards."""

    async def test_confirmed_cheat_excludes_run_entry(self, db_session: AsyncSession):
        """Test that confirming a flag as cheat excludes the run entry from rankings."""
        # Create test entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-exclude")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_exclude_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.NA,
            board_type=BoardType.RUN_RUNS,
        )

        # Submit a score
        score_service = ScoreService(db_session)
        event, run_entry, _ = await score_service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=1000.0,
            player_name="TestPlayer",
        )

        # Create a flag on the event
        flag_service = ScoreFlagService(db_session)
        flag = ScoreFlag(
            score_event_id=event.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_service.repository.create(flag)

        # Verify run entry exists and is not excluded
        run_entry_service = RunEntryService(db_session)
        entry = await run_entry_service.get_by_board_and_score_event(board.id, event.id)
        assert entry is not None
        assert entry.excluded_at is None

        # Mark as confirmed cheat
        await flag_service.update_flag(
            flag_id=created_flag.id,
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
        )

        # Verify entry is now excluded
        entry = await run_entry_service.get_by_board_and_score_event(board.id, event.id)
        assert entry is not None
        assert entry.excluded_at is not None
        assert entry.excluded_reason == "confirmed_cheat"

    async def test_false_positive_restores_run_entry(self, db_session: AsyncSession):
        """Test that marking a flag as false positive restores the run entry."""
        # Create test entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-restore")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_restore_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.NA,
            board_type=BoardType.RUN_RUNS,
        )

        # Submit a score
        score_service = ScoreService(db_session)
        event, _, _ = await score_service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=1000.0,
            player_name="TestPlayer",
        )

        # Create a flag and mark as confirmed cheat
        flag_service = ScoreFlagService(db_session)
        flag = ScoreFlag(
            score_event_id=event.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_service.repository.create(flag)
        await flag_service.update_flag(
            flag_id=created_flag.id,
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
        )

        # Verify excluded
        run_entry_service = RunEntryService(db_session)
        entry = await run_entry_service.get_by_board_and_score_event(board.id, event.id)
        assert entry is not None
        assert entry.excluded_at is not None

        # Now mark as false positive
        await flag_service.update_flag(
            flag_id=created_flag.id,
            status=ScoreFlagStatus.FALSE_POSITIVE,
        )

        # Verify restored
        entry = await run_entry_service.get_by_board_and_score_event(board.id, event.id)
        assert entry is not None
        assert entry.excluded_at is None
        assert entry.excluded_reason is None

    async def test_listing_excludes_excluded_entries(self, db_session: AsyncSession):
        """Test that listing run entries excludes those marked as excluded."""
        # Create test entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-listing")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_test_listing_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.NA,
            board_type=BoardType.RUN_RUNS,
        )

        # Submit multiple scores
        score_service = ScoreService(db_session)
        event1, _, _ = await score_service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=1000.0,
            player_name="TestPlayer",
        )
        _, _, _ = await score_service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=2000.0,
            player_name="TestPlayer",
        )

        # List should show 2 entries
        run_entry_service = RunEntryService(db_session)
        result = await run_entry_service.list_run_entries(board_id=board.id)
        assert len(result.items) == 2

        # Flag and confirm cheat on first event
        flag_service = ScoreFlagService(db_session)
        flag = ScoreFlag(
            score_event_id=event1.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_service.repository.create(flag)
        await flag_service.update_flag(
            flag_id=created_flag.id,
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
        )

        # List should now show only 1 entry
        result = await run_entry_service.list_run_entries(board_id=board.id)
        assert len(result.items) == 1
        assert result.items[0].primary_value == 2000.0


@pytest.mark.asyncio
class TestRankingSyncEdgeCases:
    """Test edge cases in ranking sync."""

    async def test_sync_ranking_no_op_for_pending_status(self, db_session: AsyncSession):
        """Test that pending status doesn't trigger any ranking updates."""
        # Create test entities
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-pending")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_pending_test",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.NA,
            board_type=BoardType.RUN_RUNS,
        )

        # Submit a score
        score_service = ScoreService(db_session)
        event, _, _ = await score_service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=1000.0,
            player_name="TestPlayer",
        )

        # Create a flag as confirmed cheat first
        flag_service = ScoreFlagService(db_session)
        flag = ScoreFlag(
            score_event_id=event.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
        )
        created_flag = await flag_service.repository.create(flag)

        # Verify excluded
        run_entry_service = RunEntryService(db_session)
        entry = await run_entry_service.get_by_board_and_score_event(board.id, event.id)
        assert entry is not None

        # Exclude first
        await flag_service.update_flag(
            flag_id=created_flag.id,
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
        )

        entry = await run_entry_service.get_by_board_and_score_event(board.id, event.id)
        assert entry is not None
        assert entry.excluded_at is not None

        # Now update to PENDING - this should NOT change exclusion
        # (The status doesn't trigger restoration)
        await flag_service.update_flag(
            flag_id=created_flag.id,
            status=ScoreFlagStatus.PENDING,
        )

        # Entry should still be excluded
        entry = await run_entry_service.get_by_board_and_score_event(board.id, event.id)
        assert entry is not None
        # Status is PENDING, which doesn't restore (only FALSE_POSITIVE/DISMISSED do)
        assert entry.excluded_at is not None

    async def test_dismissed_restores_run_entry(self, db_session: AsyncSession):
        """Test that dismissed status restores the run entry."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-dismissed")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_dismissed_test",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.NA,
            board_type=BoardType.RUN_RUNS,
        )

        score_service = ScoreService(db_session)
        event, _, _ = await score_service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=1000.0,
            player_name="TestPlayer",
        )

        flag_service = ScoreFlagService(db_session)
        flag = ScoreFlag(
            score_event_id=event.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_service.repository.create(flag)

        # Mark as cheat first
        await flag_service.update_flag(
            flag_id=created_flag.id,
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
        )

        run_entry_service = RunEntryService(db_session)
        entry = await run_entry_service.get_by_board_and_score_event(board.id, event.id)
        assert entry is not None
        assert entry.excluded_at is not None

        # Now mark as dismissed
        await flag_service.update_flag(
            flag_id=created_flag.id,
            status=ScoreFlagStatus.DISMISSED,
        )

        entry = await run_entry_service.get_by_board_and_score_event(board.id, event.id)
        assert entry is not None
        assert entry.excluded_at is None
        assert entry.excluded_reason is None


@pytest.mark.asyncio
class TestRankingSyncForRunIdentity:
    """Test ranking sync for RUN_IDENTITY boards."""

    async def test_confirmed_cheat_recomputes_selected_event(self, db_session: AsyncSession):
        """Test that confirming a flag recomputes board state when flagged event is selected."""

        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-ri-cheat")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_ri_test_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="High Scores",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
            board_type=BoardType.RUN_IDENTITY,
        )

        # Submit two scores - 1000 (best) and 500
        score_service = ScoreService(db_session)
        event1, _, _ = await score_service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=1000.0,
            player_name="TestPlayer",
        )

        event2, _, _ = await score_service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=500.0,
            player_name="TestPlayer",
        )

        # Verify state shows 1000 (best score)
        state_service = BoardStateService(db_session)
        state = await state_service.get_by_board_and_identity(board.id, identity.id)
        assert state is not None
        assert state.primary_value == 1000.0

        # Flag the best score as cheat
        flag_service = ScoreFlagService(db_session)
        flag = ScoreFlag(
            score_event_id=event1.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_service.repository.create(flag)

        # Confirm cheat
        await flag_service.update_flag(
            flag_id=created_flag.id,
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
        )

        # State should now show 500 (next best)
        state = await state_service.get_by_board_and_identity(board.id, identity.id)
        assert state is not None
        assert state.primary_value == 500.0

    async def test_confirmed_cheat_no_op_for_non_selected_event(self, db_session: AsyncSession):
        """Test that confirming a flag on non-selected event doesn't change state."""

        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-ri-noop")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_ri_noop_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="High Scores",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
            board_type=BoardType.RUN_IDENTITY,
        )

        score_service = ScoreService(db_session)
        # Submit 1000 first (will be best), then 500
        event1, _, _ = await score_service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=1000.0,
            player_name="TestPlayer",
        )

        event2, _, _ = await score_service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=500.0,
            player_name="TestPlayer",
        )

        state_service = BoardStateService(db_session)
        state = await state_service.get_by_board_and_identity(board.id, identity.id)
        assert state is not None
        assert state.primary_value == 1000.0

        # Flag the NON-selected score (500)
        flag_service = ScoreFlagService(db_session)
        flag = ScoreFlag(
            score_event_id=event2.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_service.repository.create(flag)

        await flag_service.update_flag(
            flag_id=created_flag.id,
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
        )

        # State should still show 1000 (unchanged)
        state = await state_service.get_by_board_and_identity(board.id, identity.id)
        assert state is not None
        assert state.primary_value == 1000.0

    async def test_confirmed_cheat_clears_state_when_no_eligible_events(
        self, db_session: AsyncSession
    ):
        """Test that state is cleared when all events are flagged."""

        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-ri-clear")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_ri_clear_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="High Scores",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
            board_type=BoardType.RUN_IDENTITY,
        )

        score_service = ScoreService(db_session)
        event, _, _ = await score_service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=1000.0,
            player_name="TestPlayer",
        )

        state_service = BoardStateService(db_session)
        state = await state_service.get_by_board_and_identity(board.id, identity.id)
        assert state is not None
        assert state.primary_value == 1000.0

        # Flag the only score as cheat
        flag_service = ScoreFlagService(db_session)
        flag = ScoreFlag(
            score_event_id=event.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_service.repository.create(flag)

        await flag_service.update_flag(
            flag_id=created_flag.id,
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
        )

        # State should now have NULL primary_value
        state = await state_service.get_by_board_and_identity(board.id, identity.id)
        assert state is not None
        assert state.primary_value is None

    async def test_recompute_with_first_keep_strategy(self, db_session: AsyncSession):
        """Test recomputation with FIRST keep strategy."""

        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-ri-first")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_ri_first_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="First Score Board",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.FIRST,
            board_type=BoardType.RUN_IDENTITY,
        )

        score_service = ScoreService(db_session)
        # Submit 500 first, then 1000
        event1, _, _ = await score_service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=500.0,
            player_name="TestPlayer",
        )

        event2, _, _ = await score_service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=1000.0,
            player_name="TestPlayer",
        )

        state_service = BoardStateService(db_session)
        state = await state_service.get_by_board_and_identity(board.id, identity.id)
        assert state is not None
        # FIRST keeps the first submission
        assert state.primary_value == 500.0

        # Flag the first score as cheat
        flag_service = ScoreFlagService(db_session)
        flag = ScoreFlag(
            score_event_id=event1.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_service.repository.create(flag)

        await flag_service.update_flag(
            flag_id=created_flag.id,
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
        )

        # Now should show 1000 (next first eligible)
        state = await state_service.get_by_board_and_identity(board.id, identity.id)
        assert state is not None
        assert state.primary_value == 1000.0

    async def test_recompute_with_latest_keep_strategy(self, db_session: AsyncSession):
        """Test recomputation with LATEST keep strategy."""

        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-ri-latest")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_ri_latest_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Latest Score Board",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.LATEST,
            board_type=BoardType.RUN_IDENTITY,
        )

        score_service = ScoreService(db_session)
        event1, _, _ = await score_service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=500.0,
            player_name="TestPlayer",
        )

        event2, _, _ = await score_service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=1000.0,
            player_name="TestPlayer",
        )

        state_service = BoardStateService(db_session)
        state = await state_service.get_by_board_and_identity(board.id, identity.id)
        assert state is not None
        # LATEST keeps the latest submission
        assert state.primary_value == 1000.0

        # Flag the latest score as cheat
        flag_service = ScoreFlagService(db_session)
        flag = ScoreFlag(
            score_event_id=event2.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_service.repository.create(flag)

        await flag_service.update_flag(
            flag_id=created_flag.id,
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
        )

        # Now should show 500 (next latest eligible)
        state = await state_service.get_by_board_and_identity(board.id, identity.id)
        assert state is not None
        assert state.primary_value == 500.0

    async def test_recompute_with_ascending_sort(self, db_session: AsyncSession):
        """Test recomputation with ASCENDING sort direction (lower is better)."""

        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-ri-asc")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_ri_asc_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speedrun Board",
            sort_direction=SortDirection.ASCENDING,  # Lower is better
            keep_strategy=KeepStrategy.BEST,
            board_type=BoardType.RUN_IDENTITY,
        )

        score_service = ScoreService(db_session)
        # Submit 100 (best in ascending) and 200
        event1, _, _ = await score_service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=100.0,
            player_name="TestPlayer",
        )

        event2, _, _ = await score_service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=200.0,
            player_name="TestPlayer",
        )

        state_service = BoardStateService(db_session)
        state = await state_service.get_by_board_and_identity(board.id, identity.id)
        assert state is not None
        # ASCENDING means 100 is best
        assert state.primary_value == 100.0

        # Flag the best score as cheat
        flag_service = ScoreFlagService(db_session)
        flag = ScoreFlag(
            score_event_id=event1.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_service.repository.create(flag)

        await flag_service.update_flag(
            flag_id=created_flag.id,
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
        )

        # Now should show 200 (next best in ascending)
        state = await state_service.get_by_board_and_identity(board.id, identity.id)
        assert state is not None
        assert state.primary_value == 200.0


@pytest.mark.asyncio
class TestRankingSyncForCounter:
    """Test ranking sync for COUNTER boards."""

    async def test_confirmed_cheat_recomputes_counter(self, db_session: AsyncSession):
        """Test that confirming a cheat recomputes the counter total."""

        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-counter-ch")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_counter_test_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Kill Counter",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.NA,
            board_type=BoardType.COUNTER,
        )

        score_service = ScoreService(db_session)
        # Submit several deltas: 10 + 20 + 30 = 60
        event1, _, _ = await score_service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            delta=10.0,
            player_name="TestPlayer",
        )

        event2, _, _ = await score_service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            delta=20.0,
            player_name="TestPlayer",
        )

        event3, _, _ = await score_service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            delta=30.0,
            player_name="TestPlayer",
        )

        state_service = BoardStateService(db_session)
        state = await state_service.get_by_board_and_identity(board.id, identity.id)
        assert state is not None
        assert state.primary_value == 60.0

        # Flag the second delta (20) as cheat
        flag_service = ScoreFlagService(db_session)
        flag = ScoreFlag(
            score_event_id=event2.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_service.repository.create(flag)

        await flag_service.update_flag(
            flag_id=created_flag.id,
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
        )

        # Counter should now be 10 + 30 = 40
        state = await state_service.get_by_board_and_identity(board.id, identity.id)
        assert state is not None
        assert state.primary_value == 40.0

    async def test_counter_zero_when_all_events_flagged(self, db_session: AsyncSession):
        """Test that counter goes to 0 when all events are flagged."""

        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-cnt-zero")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_counter_zero_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Kill Counter",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.NA,
            board_type=BoardType.COUNTER,
        )

        score_service = ScoreService(db_session)
        event, _, _ = await score_service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            delta=50.0,
            player_name="TestPlayer",
        )

        state_service = BoardStateService(db_session)
        state = await state_service.get_by_board_and_identity(board.id, identity.id)
        assert state is not None
        assert state.primary_value == 50.0

        # Flag the only event as cheat
        flag_service = ScoreFlagService(db_session)
        flag = ScoreFlag(
            score_event_id=event.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_service.repository.create(flag)

        await flag_service.update_flag(
            flag_id=created_flag.id,
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
        )

        # Counter should now be 0
        state = await state_service.get_by_board_and_identity(board.id, identity.id)
        assert state is not None
        assert state.primary_value == 0.0


@pytest.mark.asyncio
class TestReviewFlag:
    """Test the review_flag method."""

    async def test_review_flag_confirms_cheat(self, db_session: AsyncSession):
        """Test review_flag method with confirmed cheat status."""

        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-review-1")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_review_test_1",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.NA,
            board_type=BoardType.RUN_RUNS,
        )

        score_service = ScoreService(db_session)
        event, _, _ = await score_service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=1000.0,
            player_name="TestPlayer",
        )

        flag_service = ScoreFlagService(db_session)
        flag = ScoreFlag(
            score_event_id=event.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_service.repository.create(flag)

        reviewer_id = UserID()
        reviewed_flag = await flag_service.review_flag(
            flag_id=created_flag.id,
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
            reviewer_decision="Verified cheating",
            reviewer_id=reviewer_id,
        )

        assert reviewed_flag.status == ScoreFlagStatus.CONFIRMED_CHEAT
        assert reviewed_flag.reviewer_decision == "Verified cheating"
        assert reviewed_flag.reviewer_id == reviewer_id
        assert reviewed_flag.reviewed_at is not None

    async def test_review_flag_false_positive(self, db_session: AsyncSession):
        """Test review_flag method with false positive status."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test Account", slug="test-review-2")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_review_test_2",
            display_name="TestPlayer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Test Board",
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.NA,
            board_type=BoardType.RUN_RUNS,
        )

        score_service = ScoreService(db_session)
        event, _, _ = await score_service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=1000.0,
            player_name="TestPlayer",
        )

        flag_service = ScoreFlagService(db_session)
        flag = ScoreFlag(
            score_event_id=event.id,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            metadata={"reason": "test"},
            status=ScoreFlagStatus.PENDING,
        )
        created_flag = await flag_service.repository.create(flag)

        reviewed_flag = await flag_service.review_flag(
            flag_id=created_flag.id,
            status=ScoreFlagStatus.FALSE_POSITIVE,
            reviewer_decision="Legitimate gameplay",
        )

        assert reviewed_flag.status == ScoreFlagStatus.FALSE_POSITIVE
        assert reviewed_flag.reviewer_decision == "Legitimate gameplay"
        assert reviewed_flag.reviewed_at is not None

    async def test_review_flag_not_found(self, db_session: AsyncSession):
        """Test review_flag raises error for non-existent flag."""

        flag_service = ScoreFlagService(db_session)

        with pytest.raises(EntityNotFoundError):
            await flag_service.review_flag(
                flag_id=ScoreFlagID(),
                status=ScoreFlagStatus.CONFIRMED_CHEAT,
            )
