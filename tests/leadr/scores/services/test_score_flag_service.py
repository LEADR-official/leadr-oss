"""Tests for ScoreFlagService."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from leadr.boards.domain.board import Board, BoardType, KeepStrategy
from leadr.boards.domain.board import SortDirection as BoardSortDirection
from leadr.boards.domain.board_state import BoardState
from leadr.boards.domain.run_entry import RunEntry
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import (
    AccountID,
    BoardID,
    GameID,
    IdentityID,
    ScoreEventID,
    ScoreFlagID,
    UserID,
)
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.scores.domain.anti_cheat.enums import (
    FlagConfidence,
    FlagType,
    ScoreFlagStatus,
)
from leadr.scores.domain.anti_cheat.models import ScoreFlag
from leadr.scores.domain.score_event import ScoreEvent
from leadr.scores.services.score_flag_service import ScoreFlagService


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    return AsyncMock()


@pytest.fixture
def service(mock_session):
    """Create service with mocked repository."""
    svc = ScoreFlagService(mock_session)
    svc.repository = MagicMock()
    return svc


def _make_flag(
    flag_id: ScoreFlagID | None = None,
    score_event_id: ScoreEventID | None = None,
    status: ScoreFlagStatus = ScoreFlagStatus.PENDING,
    **kwargs,
) -> ScoreFlag:
    """Create a ScoreFlag for testing."""
    flag = ScoreFlag(
        score_event_id=score_event_id or ScoreEventID(),
        flag_type=kwargs.pop("flag_type", FlagType.VELOCITY),
        confidence=kwargs.pop("confidence", FlagConfidence.HIGH),
        metadata=kwargs.pop("metadata", {"reason": "test"}),
        status=status,
        **kwargs,
    )
    if flag_id:
        flag = flag.model_copy(update={"id": flag_id})
    return flag


def _make_event(
    board_id: BoardID | None = None,
    identity_id: IdentityID | None = None,
    **kwargs,
) -> ScoreEvent:
    """Create a ScoreEvent for testing."""
    return ScoreEvent(
        account_id=kwargs.pop("account_id", AccountID()),
        game_id=kwargs.pop("game_id", GameID()),
        board_id=board_id or BoardID(),
        identity_id=identity_id or IdentityID(),
        event_payload=kwargs.pop("event_payload", {"value": 100.0}),
        **kwargs,
    )


def _make_board(
    board_id: BoardID | None = None,
    board_type: BoardType = BoardType.RUN_IDENTITY,
    keep_strategy: KeepStrategy | None = None,
    sort_direction: BoardSortDirection = BoardSortDirection.DESCENDING,
) -> Board:
    """Create a Board for testing."""
    bid = board_id or BoardID()
    if keep_strategy is None:
        # RUN_RUNS and COUNTER require NA, RUN_IDENTITY defaults to BEST
        if board_type in (BoardType.RUN_RUNS, BoardType.COUNTER, BoardType.RATIO):
            keep_strategy = KeepStrategy.NA
        else:
            keep_strategy = KeepStrategy.BEST
    return Board(
        account_id=AccountID(),
        game_id=GameID(),
        name="Test Board",
        slug="test-board",
        short_code="TB",
        sort_direction=sort_direction,
        board_type=board_type,
        keep_strategy=keep_strategy,
    ).model_copy(update={"id": bid})


def _make_board_state(
    board_id: BoardID,
    identity_id: IdentityID,
    primary_value: float | None = 100.0,
    aux: dict | None = None,
) -> BoardState:
    """Create a BoardState for testing."""
    return BoardState(
        board_id=board_id,
        identity_id=identity_id,
        primary_value=primary_value,
        aux=aux,
    )


def _make_run_entry(
    board_id: BoardID,
    identity_id: IdentityID,
    score_event_id: ScoreEventID,
    primary_value: float = 100.0,
) -> RunEntry:
    """Create a RunEntry for testing."""
    return RunEntry(
        board_id=board_id,
        identity_id=identity_id,
        score_event_id=score_event_id,
        primary_value=primary_value,
    )


@pytest.mark.asyncio
class TestScoreFlagService:
    """Test suite for ScoreFlagService."""

    async def test_get_flag(self, service):
        """Test getting a flag by ID."""
        flag_id = ScoreFlagID()
        expected_flag = _make_flag(flag_id=flag_id)

        service.repository.get_by_id = AsyncMock(return_value=expected_flag)

        result = await service.get_flag(flag_id)

        assert result is not None
        assert result.id == flag_id
        assert result.flag_type == FlagType.VELOCITY
        service.repository.get_by_id.assert_awaited_once_with(flag_id)

    async def test_get_flag_returns_none_for_nonexistent(self, service):
        """Test get_flag returns None for nonexistent flag."""
        flag_id = ScoreFlagID(uuid4())
        service.repository.get_by_id = AsyncMock(return_value=None)

        result = await service.get_flag(flag_id)

        assert result is None
        service.repository.get_by_id.assert_awaited_once_with(flag_id)

    async def test_list_flags(self, service):
        """Test list_flags delegates to repository.filter with correct args."""
        account_id = AccountID()
        board_id = BoardID()
        pagination = PaginationParams(cursor=None, limit=50, sort=None)
        expected = PaginatedResult(
            items=[_make_flag()],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )
        service.repository.filter = AsyncMock(return_value=expected)

        result = await service.list_flags(
            account_id=account_id,
            board_id=board_id,
            game_id=None,
            status="pending",
            flag_type="VELOCITY",
            pagination=pagination,
        )

        assert result == expected
        service.repository.filter.assert_awaited_once_with(
            account_id=account_id,
            board_id=board_id,
            game_id=None,
            status="pending",
            flag_type="VELOCITY",
            pagination=pagination,
        )

    async def test_update_flag_with_status_only(self, service):
        """Test updating a flag with status only."""
        flag_id = ScoreFlagID()
        original_flag = _make_flag(flag_id=flag_id)

        service.repository.get_by_id = AsyncMock(return_value=original_flag)
        updated_flag = _make_flag(
            flag_id=flag_id,
            status=ScoreFlagStatus.FALSE_POSITIVE,
            reviewed_at=datetime.now(UTC),
        )
        service.repository.update = AsyncMock(return_value=updated_flag)
        service._sync_ranking_status = AsyncMock()

        result = await service.update_flag(
            flag_id=flag_id,
            status=ScoreFlagStatus.FALSE_POSITIVE,
        )

        assert result.status == ScoreFlagStatus.FALSE_POSITIVE
        service.repository.update.assert_awaited_once()
        service._sync_ranking_status.assert_awaited_once()

    async def test_update_flag_with_reviewer_decision_only(self, service):
        """Test updating a flag with reviewer decision only (no sync)."""
        flag_id = ScoreFlagID()
        original_flag = _make_flag(flag_id=flag_id)

        service.repository.get_by_id = AsyncMock(return_value=original_flag)
        updated_flag = _make_flag(
            flag_id=flag_id,
            reviewer_decision="Looks suspicious",
        )
        service.repository.update = AsyncMock(return_value=updated_flag)

        result = await service.update_flag(
            flag_id=flag_id,
            reviewer_decision="Looks suspicious",
        )

        assert result.reviewer_decision == "Looks suspicious"
        assert result.status == ScoreFlagStatus.PENDING
        service.repository.update.assert_awaited_once()

    async def test_update_flag_with_string_status(self, service):
        """Test update_flag converts string status to enum."""
        flag_id = ScoreFlagID()
        original_flag = _make_flag(flag_id=flag_id)

        service.repository.get_by_id = AsyncMock(return_value=original_flag)
        service.repository.update = AsyncMock(return_value=original_flag)
        service._sync_ranking_status = AsyncMock()

        await service.update_flag(flag_id=flag_id, status="confirmed_cheat")

        # _sync_ranking_status should have been called with the enum value
        service._sync_ranking_status.assert_awaited_once()
        call_args = service._sync_ranking_status.call_args
        assert call_args[0][1] == ScoreFlagStatus.CONFIRMED_CHEAT


@pytest.mark.asyncio
class TestReviewFlag:
    """Test the review_flag method."""

    async def test_review_flag_confirms_cheat(self, service):
        """Test review_flag method with confirmed cheat status."""
        flag_id = ScoreFlagID()
        reviewer_id = UserID()
        original_flag = _make_flag(flag_id=flag_id)

        service.repository.get_by_id = AsyncMock(return_value=original_flag)
        updated_flag = _make_flag(
            flag_id=flag_id,
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
            reviewer_decision="Verified cheating",
            reviewer_id=reviewer_id,
            reviewed_at=datetime.now(UTC),
        )
        service.repository.update = AsyncMock(return_value=updated_flag)
        service._sync_ranking_status = AsyncMock()

        result = await service.review_flag(
            flag_id=flag_id,
            status=ScoreFlagStatus.CONFIRMED_CHEAT,
            reviewer_decision="Verified cheating",
            reviewer_id=reviewer_id,
        )

        assert result.status == ScoreFlagStatus.CONFIRMED_CHEAT
        assert result.reviewer_id == reviewer_id
        service._sync_ranking_status.assert_awaited_once()

    async def test_review_flag_false_positive(self, service):
        """Test review_flag method with false positive status."""
        flag_id = ScoreFlagID()
        original_flag = _make_flag(flag_id=flag_id)

        service.repository.get_by_id = AsyncMock(return_value=original_flag)
        updated_flag = _make_flag(
            flag_id=flag_id,
            status=ScoreFlagStatus.FALSE_POSITIVE,
            reviewed_at=datetime.now(UTC),
        )
        service.repository.update = AsyncMock(return_value=updated_flag)
        service._sync_ranking_status = AsyncMock()

        result = await service.review_flag(
            flag_id=flag_id,
            status=ScoreFlagStatus.FALSE_POSITIVE,
            reviewer_decision="Legitimate gameplay",
        )

        assert result.status == ScoreFlagStatus.FALSE_POSITIVE
        service._sync_ranking_status.assert_awaited_once()

    async def test_review_flag_not_found(self, service):
        """Test review_flag raises error for non-existent flag."""
        flag_id = ScoreFlagID()
        service.repository.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError):
            await service.review_flag(
                flag_id=flag_id,
                status=ScoreFlagStatus.CONFIRMED_CHEAT,
            )


# --- Tests for _sync_ranking_status and downstream methods ---

MODULE = "leadr.scores.services.score_flag_service"


@pytest.mark.asyncio
class TestSyncRankingStatus:
    """Test _sync_ranking_status orchestration."""

    async def test_event_not_found_returns_early(self, service):
        """When score event is not found, sync returns without action."""
        flag = _make_flag()

        with patch(f"{MODULE}.ScoreEventService") as mock_event_svc:
            mock_event_svc.return_value.get_score_event = AsyncMock(return_value=None)
            await service._sync_ranking_status(flag, ScoreFlagStatus.CONFIRMED_CHEAT)

        # No BoardService call should happen
        # (just verifying no exception)

    async def test_board_not_found_returns_early(self, service):
        """When board is not found, sync returns without action."""
        flag = _make_flag()
        event = _make_event()

        with (
            patch(f"{MODULE}.ScoreEventService") as mock_event_svc,
            patch(f"{MODULE}.BoardService") as mock_board_svc,
        ):
            mock_event_svc.return_value.get_score_event = AsyncMock(return_value=event)
            mock_board_svc.return_value.get_board = AsyncMock(return_value=None)
            await service._sync_ranking_status(flag, ScoreFlagStatus.CONFIRMED_CHEAT)

    async def test_pending_status_no_action(self, service):
        """PENDING status triggers no sync action."""
        flag = _make_flag()
        event = _make_event()
        board = _make_board(board_type=BoardType.RUN_RUNS)

        with (
            patch(f"{MODULE}.ScoreEventService") as mock_event_svc,
            patch(f"{MODULE}.BoardService") as mock_board_svc,
        ):
            mock_event_svc.return_value.get_score_event = AsyncMock(return_value=event)
            mock_board_svc.return_value.get_board = AsyncMock(return_value=board)

            service._sync_run_runs_entry = AsyncMock()
            await service._sync_ranking_status(flag, ScoreFlagStatus.PENDING)
            service._sync_run_runs_entry.assert_not_awaited()

    async def test_confirmed_cheat_on_run_runs_board(self, service):
        """CONFIRMED_CHEAT on RUN_RUNS board calls _sync_run_runs_entry with exclude=True."""
        board = _make_board(board_type=BoardType.RUN_RUNS)
        event = _make_event(board_id=board.id)
        flag = _make_flag(score_event_id=event.id)

        with (
            patch(f"{MODULE}.ScoreEventService") as mock_event_svc,
            patch(f"{MODULE}.BoardService") as mock_board_svc,
        ):
            mock_event_svc.return_value.get_score_event = AsyncMock(return_value=event)
            mock_board_svc.return_value.get_board = AsyncMock(return_value=board)
            service._sync_run_runs_entry = AsyncMock()

            await service._sync_ranking_status(flag, ScoreFlagStatus.CONFIRMED_CHEAT)

            service._sync_run_runs_entry.assert_awaited_once_with(
                board_id=board.id,
                score_event_id=flag.score_event_id,
                exclude=True,
            )

    async def test_false_positive_on_run_identity_board(self, service):
        """FALSE_POSITIVE on RUN_IDENTITY board calls _sync_run_identity_state."""
        board = _make_board(board_type=BoardType.RUN_IDENTITY)
        event = _make_event(board_id=board.id)
        flag = _make_flag(score_event_id=event.id)

        with (
            patch(f"{MODULE}.ScoreEventService") as mock_event_svc,
            patch(f"{MODULE}.BoardService") as mock_board_svc,
        ):
            mock_event_svc.return_value.get_score_event = AsyncMock(return_value=event)
            mock_board_svc.return_value.get_board = AsyncMock(return_value=board)
            service._sync_run_identity_state = AsyncMock()
            service._sync_ratio_dependents = AsyncMock()

            await service._sync_ranking_status(flag, ScoreFlagStatus.FALSE_POSITIVE)

            service._sync_run_identity_state.assert_awaited_once()
            service._sync_ratio_dependents.assert_awaited_once_with(board.id, event.identity_id)

    async def test_confirmed_cheat_on_counter_board(self, service):
        """CONFIRMED_CHEAT on COUNTER board calls _sync_counter_state and ratio dependents."""
        board = _make_board(board_type=BoardType.COUNTER)
        event = _make_event(board_id=board.id)
        flag = _make_flag(score_event_id=event.id)

        with (
            patch(f"{MODULE}.ScoreEventService") as mock_event_svc,
            patch(f"{MODULE}.BoardService") as mock_board_svc,
        ):
            mock_event_svc.return_value.get_score_event = AsyncMock(return_value=event)
            mock_board_svc.return_value.get_board = AsyncMock(return_value=board)
            service._sync_counter_state = AsyncMock()
            service._sync_ratio_dependents = AsyncMock()

            await service._sync_ranking_status(flag, ScoreFlagStatus.CONFIRMED_CHEAT)

            service._sync_counter_state.assert_awaited_once_with(
                board=board, identity_id=event.identity_id
            )
            service._sync_ratio_dependents.assert_awaited_once()


@pytest.mark.asyncio
class TestSyncRunRunsEntry:
    """Test _sync_run_runs_entry."""

    async def test_exclude_entry(self, service):
        """Excluding sets excluded_at and excluded_reason."""
        board_id = BoardID()
        event_id = ScoreEventID()
        entry = _make_run_entry(board_id, IdentityID(), event_id)

        with patch(f"{MODULE}.RunEntryService") as mock_run_svc:
            mock_svc = mock_run_svc.return_value
            mock_svc.get_by_board_and_score_event = AsyncMock(return_value=entry)
            mock_svc.repository.update = AsyncMock()

            await service._sync_run_runs_entry(board_id, event_id, exclude=True)

            assert entry.excluded_at is not None
            assert entry.excluded_reason == "confirmed_cheat"
            mock_svc.repository.update.assert_awaited_once_with(entry)

    async def test_restore_entry(self, service):
        """Restoring clears excluded_at and excluded_reason."""
        board_id = BoardID()
        event_id = ScoreEventID()
        entry = _make_run_entry(board_id, IdentityID(), event_id)
        entry.excluded_at = datetime.now(UTC)
        entry.excluded_reason = "confirmed_cheat"

        with patch(f"{MODULE}.RunEntryService") as mock_run_svc:
            mock_svc = mock_run_svc.return_value
            mock_svc.get_by_board_and_score_event = AsyncMock(return_value=entry)
            mock_svc.repository.update = AsyncMock()

            await service._sync_run_runs_entry(board_id, event_id, exclude=False)

            assert entry.excluded_at is None
            assert entry.excluded_reason is None
            mock_svc.repository.update.assert_awaited_once_with(entry)

    async def test_entry_not_found(self, service):
        """When entry doesn't exist, returns without action."""
        with patch(f"{MODULE}.RunEntryService") as mock_run_svc:
            mock_svc = mock_run_svc.return_value
            mock_svc.get_by_board_and_score_event = AsyncMock(return_value=None)
            mock_svc.repository.update = AsyncMock()

            await service._sync_run_runs_entry(BoardID(), ScoreEventID(), exclude=True)

            mock_svc.repository.update.assert_not_awaited()


@pytest.mark.asyncio
class TestSyncRunIdentityState:
    """Test _sync_run_identity_state."""

    async def test_state_not_found(self, service):
        """When board state doesn't exist, returns early."""
        board = _make_board()
        with patch(f"{MODULE}.BoardStateService") as mock_state_svc:
            mock_state_svc.return_value.get_by_board_and_identity = AsyncMock(return_value=None)
            service._recompute_run_identity = AsyncMock()

            await service._sync_run_identity_state(board, IdentityID(), ScoreEventID())

            service._recompute_run_identity.assert_not_awaited()

    async def test_flagged_event_not_selected(self, service):
        """When flagged event is not the selected one, no recompute."""
        board = _make_board()
        identity_id = IdentityID()
        flagged_event_id = ScoreEventID()
        state = _make_board_state(
            board.id, identity_id, aux={"selected_event_id": str(ScoreEventID())}
        )

        with patch(f"{MODULE}.BoardStateService") as mock_state_svc:
            mock_state_svc.return_value.get_by_board_and_identity = AsyncMock(return_value=state)
            service._recompute_run_identity = AsyncMock()

            await service._sync_run_identity_state(board, identity_id, flagged_event_id)

            service._recompute_run_identity.assert_not_awaited()

    async def test_flagged_event_is_selected_triggers_recompute(self, service):
        """When flagged event IS the selected one, triggers recompute."""
        board = _make_board()
        identity_id = IdentityID()
        flagged_event_id = ScoreEventID()
        state = _make_board_state(
            board.id, identity_id, aux={"selected_event_id": str(flagged_event_id)}
        )

        with patch(f"{MODULE}.BoardStateService") as mock_state_svc:
            mock_state_svc.return_value.get_by_board_and_identity = AsyncMock(return_value=state)
            service._recompute_run_identity = AsyncMock()

            await service._sync_run_identity_state(board, identity_id, flagged_event_id)

            service._recompute_run_identity.assert_awaited_once_with(board, identity_id, state)


@pytest.mark.asyncio
class TestRecomputeRunIdentity:
    """Test _recompute_run_identity."""

    async def test_eligible_event_found(self, mock_session, service):
        """When an eligible event exists, updates state with its value."""
        board = _make_board(keep_strategy=KeepStrategy.BEST)
        identity_id = IdentityID()
        state = _make_board_state(board.id, identity_id, aux={"event_count": 3})

        # Mock the eligible event ORM result
        mock_event = MagicMock()
        mock_event.id = uuid4()
        mock_event.event_payload = {"value": 500.0}
        mock_event.timezone = "US/Eastern"
        mock_event.country = "US"
        mock_event.city = "Boston"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_event
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(f"{MODULE}.BoardStateService") as mock_state_svc:
            mock_state_svc.return_value.repository.update = AsyncMock()

            await service._recompute_run_identity(board, identity_id, state)

            assert state.primary_value == 500.0
            assert state.aux is not None
            assert state.aux["selected_event_id"] == str(mock_event.id)
            assert state.aux["event_count"] == 3
            assert state.timezone == "US/Eastern"
            assert state.country == "US"
            assert state.city == "Boston"
            mock_state_svc.return_value.repository.update.assert_awaited_once_with(state)

    async def test_no_eligible_event(self, mock_session, service):
        """When no eligible event exists, sets primary_value to None."""
        board = _make_board(keep_strategy=KeepStrategy.FIRST)
        identity_id = IdentityID()
        state = _make_board_state(board.id, identity_id, aux={"event_count": 2})

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(f"{MODULE}.BoardStateService") as mock_state_svc:
            mock_state_svc.return_value.repository.update = AsyncMock()

            await service._recompute_run_identity(board, identity_id, state)

            assert state.primary_value is None
            assert state.aux is not None
            assert state.aux["selected_event_id"] is None
            assert state.aux["event_count"] == 2

    async def test_keep_strategy_latest(self, mock_session, service):
        """LATEST keep_strategy exercises the correct branch."""
        board = _make_board(keep_strategy=KeepStrategy.LATEST)
        identity_id = IdentityID()
        state = _make_board_state(board.id, identity_id, aux={"event_count": 1})

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(f"{MODULE}.BoardStateService") as mock_state_svc:
            mock_state_svc.return_value.repository.update = AsyncMock()
            await service._recompute_run_identity(board, identity_id, state)

        assert state.primary_value is None

    async def test_keep_strategy_best_ascending(self, mock_session, service):
        """BEST with ASCENDING sort direction exercises the ascending branch."""
        board = _make_board(
            keep_strategy=KeepStrategy.BEST,
            sort_direction=BoardSortDirection.ASCENDING,
        )
        identity_id = IdentityID()
        state = _make_board_state(board.id, identity_id, aux={"event_count": 1})

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(f"{MODULE}.BoardStateService") as mock_state_svc:
            mock_state_svc.return_value.repository.update = AsyncMock()
            await service._recompute_run_identity(board, identity_id, state)

        assert state.primary_value is None

    async def test_keep_strategy_na_fallback(self, mock_session, service):
        """NA keep_strategy hits the else branch (fallback to created_at asc)."""
        board = _make_board(board_type=BoardType.RUN_RUNS, keep_strategy=KeepStrategy.NA)
        identity_id = IdentityID()
        state = _make_board_state(board.id, identity_id, aux={"event_count": 1})

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch(f"{MODULE}.BoardStateService") as mock_state_svc:
            mock_state_svc.return_value.repository.update = AsyncMock()
            await service._recompute_run_identity(board, identity_id, state)

        assert state.primary_value is None


@pytest.mark.asyncio
class TestSyncCounterState:
    """Test _sync_counter_state."""

    async def test_state_not_found(self, service):
        """When board state doesn't exist, returns early."""
        board = _make_board(board_type=BoardType.COUNTER)
        with patch(f"{MODULE}.BoardStateService") as mock_state_svc:
            mock_state_svc.return_value.get_by_board_and_identity = AsyncMock(return_value=None)

            await service._sync_counter_state(board, IdentityID())

    async def test_events_exist(self, mock_session, service):
        """When events exist, sets primary_value to sum of deltas."""
        board = _make_board(board_type=BoardType.COUNTER)
        identity_id = IdentityID()
        state = _make_board_state(board.id, identity_id)

        mock_row = (150.0, 5)
        mock_result = MagicMock()
        mock_result.one.return_value = mock_row

        with patch(f"{MODULE}.BoardStateService") as mock_state_svc:
            mock_state_svc.return_value.get_by_board_and_identity = AsyncMock(return_value=state)
            mock_state_svc.return_value.repository.update = AsyncMock()
            mock_session.execute = AsyncMock(return_value=mock_result)

            await service._sync_counter_state(board, identity_id)

            assert state.primary_value == 150.0
            assert state.aux == {"event_count": 5}
            mock_state_svc.return_value.repository.update.assert_awaited_once_with(state)

    async def test_no_eligible_events(self, mock_session, service):
        """When no eligible events, sets primary_value to 0."""
        board = _make_board(board_type=BoardType.COUNTER)
        identity_id = IdentityID()
        state = _make_board_state(board.id, identity_id)

        mock_row = (None, 0)
        mock_result = MagicMock()
        mock_result.one.return_value = mock_row

        with patch(f"{MODULE}.BoardStateService") as mock_state_svc:
            mock_state_svc.return_value.get_by_board_and_identity = AsyncMock(return_value=state)
            mock_state_svc.return_value.repository.update = AsyncMock()
            mock_session.execute = AsyncMock(return_value=mock_result)

            await service._sync_counter_state(board, identity_id)

            assert state.primary_value == 0.0
            assert state.aux == {"event_count": 0}


@pytest.mark.asyncio
class TestSyncRatioDependents:
    """Test _sync_ratio_dependents."""

    async def test_has_dependents(self, service):
        """When dependent configs exist, recomputes each."""
        board_id = BoardID()
        identity_id = IdentityID()
        config1 = MagicMock()
        config2 = MagicMock()

        with patch(f"{MODULE}.BoardStateService") as mock_state_svc:
            mock_svc = mock_state_svc.return_value
            mock_svc.find_dependent_ratio_boards = AsyncMock(return_value=[config1, config2])
            mock_svc.recompute_ratio_for_identity = AsyncMock()

            await service._sync_ratio_dependents(board_id, identity_id)

            assert mock_svc.recompute_ratio_for_identity.await_count == 2

    async def test_no_dependents(self, service):
        """When no dependent configs, no recomputation happens."""
        with patch(f"{MODULE}.BoardStateService") as mock_state_svc:
            mock_svc = mock_state_svc.return_value
            mock_svc.find_dependent_ratio_boards = AsyncMock(return_value=[])
            mock_svc.recompute_ratio_for_identity = AsyncMock()

            await service._sync_ratio_dependents(BoardID(), IdentityID())

            mock_svc.recompute_ratio_for_identity.assert_not_awaited()
