"""Tests for the board clearing script."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from leadr.boards.domain.board import Board, BoardType, KeepStrategy
from leadr.boards.domain.board import SortDirection as BoardSortDirection
from leadr.common.domain.ids import AccountID, BoardID, GameID, IdentityID
from leadr.common.utils.clear_board import (
    _is_board_id,
    _mode_to_is_test_filter,
    clear_board,
    count_affected_records,
    delete_records,
    get_affected_identity_ids,
    resolve_board,
)
from leadr.scores.services.score_flag_service import ScoreFlagService


def _make_board(
    board_id: BoardID | None = None,
    account_id: AccountID | None = None,
    board_type: BoardType = BoardType.RUN_IDENTITY,
    short_code: str = "TESTCODE",
) -> Board:
    """Create a Board for testing."""
    bid = board_id or BoardID()
    aid = account_id or AccountID()

    keep_strategy = KeepStrategy.NA
    if board_type == BoardType.RUN_IDENTITY:
        keep_strategy = KeepStrategy.BEST

    board = Board(
        account_id=aid,
        game_id=GameID(),
        name="Test Board",
        slug="test-board",
        short_code=short_code,
        sort_direction=BoardSortDirection.DESCENDING,
        board_type=board_type,
        keep_strategy=keep_strategy,
    )
    return board.model_copy(update={"id": bid})


class TestResolveBoardInput:
    """Tests for board input resolution (ID vs short_code)."""

    def test_detects_board_id_by_prefix(self):
        """Board ID is detected by 'brd_' prefix."""
        assert _is_board_id("brd_12345678-1234-1234-1234-123456789abc") is True
        assert _is_board_id("ABCD1234") is False
        assert _is_board_id("some_short_code") is False

    def test_detects_short_code(self):
        """Non-prefixed input is treated as short_code."""
        assert _is_board_id("ABCD1234") is False
        assert _is_board_id("XY12AB34") is False


class TestModeToFilter:
    """Tests for mode to is_test filter conversion."""

    def test_production_mode_returns_false(self):
        """Production mode filters for is_test=False."""
        assert _mode_to_is_test_filter("production") is False

    def test_test_mode_returns_true(self):
        """Test mode filters for is_test=True."""
        assert _mode_to_is_test_filter("test") is True

    def test_all_mode_returns_none(self):
        """All mode returns None (no filter)."""
        assert _mode_to_is_test_filter("all") is None


@pytest.mark.asyncio
class TestResolveBoard:
    """Tests for resolve_board function."""

    async def test_resolve_by_id(self):
        """Resolves board by ID when input starts with 'brd_'."""
        board_id = BoardID()
        account_id = AccountID()
        board = _make_board(board_id=board_id, account_id=account_id)

        mock_session = AsyncMock()
        mock_board_service = MagicMock()
        mock_board_service.get_board = AsyncMock(return_value=board)

        with patch("leadr.common.utils.clear_board.BoardService", return_value=mock_board_service):
            result = await resolve_board(mock_session, f"brd_{board_id.uuid}", str(account_id.uuid))

        assert result == board
        mock_board_service.get_board.assert_awaited_once()

    async def test_resolve_by_short_code(self):
        """Resolves board by short_code when input doesn't start with 'brd_'."""
        board_id = BoardID()
        account_id = AccountID()
        board = _make_board(board_id=board_id, account_id=account_id, short_code="ABCD1234")

        mock_session = AsyncMock()
        mock_board_service = MagicMock()
        mock_board_service.get_board_by_short_code = AsyncMock(return_value=board)

        with patch("leadr.common.utils.clear_board.BoardService", return_value=mock_board_service):
            result = await resolve_board(mock_session, "ABCD1234", str(account_id.uuid))

        assert result == board
        mock_board_service.get_board_by_short_code.assert_awaited_once_with("ABCD1234")

    async def test_board_not_found_raises_error(self):
        """Raises ValueError when board is not found."""
        mock_session = AsyncMock()
        mock_board_service = MagicMock()
        mock_board_service.get_board_by_short_code = AsyncMock(return_value=None)

        with (
            patch("leadr.common.utils.clear_board.BoardService", return_value=mock_board_service),
            pytest.raises(ValueError, match="Board not found"),
        ):
            await resolve_board(mock_session, "NOTFOUND", str(uuid4()))

    async def test_account_mismatch_raises_error(self):
        """Raises ValueError when board belongs to different account."""
        board_account_id = AccountID()
        different_account_id = AccountID()
        board = _make_board(account_id=board_account_id, short_code="ABCD1234")

        mock_session = AsyncMock()
        mock_board_service = MagicMock()
        mock_board_service.get_board_by_short_code = AsyncMock(return_value=board)

        with (
            patch("leadr.common.utils.clear_board.BoardService", return_value=mock_board_service),
            pytest.raises(ValueError, match="does not belong to account"),
        ):
            await resolve_board(mock_session, "ABCD1234", str(different_account_id.uuid))


@pytest.mark.asyncio
class TestCountAffectedRecords:
    """Tests for counting affected records."""

    async def test_counts_all_record_types(self):
        """Returns counts for all record types."""
        board_id = BoardID()
        mock_session = AsyncMock()

        # Mock execute to return different counts for each query
        mock_results = [
            MagicMock(scalar=MagicMock(return_value=100)),  # score_events
            MagicMock(scalar=MagicMock(return_value=5)),  # score_flags
            MagicMock(scalar=MagicMock(return_value=10)),  # run_entries
            MagicMock(scalar=MagicMock(return_value=50)),  # board_states
            MagicMock(scalar=MagicMock(return_value=50)),  # submission_meta
            MagicMock(scalar=MagicMock(return_value=25)),  # affected_identities
        ]
        mock_session.execute = AsyncMock(side_effect=mock_results)

        counts = await count_affected_records(mock_session, board_id, is_test_filter=False)

        assert counts["score_events"] == 100
        assert counts["score_flags"] == 5
        assert counts["run_entries"] == 10
        assert counts["board_states"] == 50
        assert counts["submission_meta"] == 50
        assert counts["affected_identities"] == 25

    async def test_counts_with_all_mode(self):
        """Counts all records when is_test_filter is None."""
        board_id = BoardID()
        mock_session = AsyncMock()

        mock_results = [
            MagicMock(scalar=MagicMock(return_value=200)),  # score_events (all)
            MagicMock(scalar=MagicMock(return_value=10)),  # score_flags
            MagicMock(scalar=MagicMock(return_value=20)),  # run_entries
            MagicMock(scalar=MagicMock(return_value=100)),  # board_states
            MagicMock(scalar=MagicMock(return_value=100)),  # submission_meta
            MagicMock(scalar=MagicMock(return_value=50)),  # affected_identities
        ]
        mock_session.execute = AsyncMock(side_effect=mock_results)

        counts = await count_affected_records(mock_session, board_id, is_test_filter=None)

        assert counts["score_events"] == 200


@pytest.mark.asyncio
class TestDeleteRecords:
    """Tests for delete_records function."""

    async def test_deletes_in_fk_order(self):
        """Deletes records in correct FK order."""
        board_id = BoardID()
        mock_session = AsyncMock()

        # Mock execute results for each delete
        mock_results = [
            MagicMock(rowcount=5),  # score_flags
            MagicMock(rowcount=10),  # run_entries
            MagicMock(rowcount=50),  # submission_meta
            MagicMock(rowcount=50),  # board_states
            MagicMock(rowcount=100),  # score_events
        ]
        mock_session.execute = AsyncMock(side_effect=mock_results)

        counts = await delete_records(mock_session, board_id, is_test_filter=False)

        assert counts["score_flags"] == 5
        assert counts["run_entries"] == 10
        assert counts["submission_meta"] == 50
        assert counts["board_states"] == 50
        assert counts["score_events"] == 100

        # Verify 5 delete queries were executed
        assert mock_session.execute.await_count == 5

    async def test_returns_zero_counts_when_empty(self):
        """Returns zero counts when no records exist."""
        board_id = BoardID()
        mock_session = AsyncMock()

        mock_results = [
            MagicMock(rowcount=0),  # score_flags
            MagicMock(rowcount=0),  # run_entries
            MagicMock(rowcount=0),  # submission_meta
            MagicMock(rowcount=0),  # board_states
            MagicMock(rowcount=0),  # score_events
        ]
        mock_session.execute = AsyncMock(side_effect=mock_results)

        counts = await delete_records(mock_session, board_id, is_test_filter=False)

        assert all(v == 0 for v in counts.values())


@pytest.mark.asyncio
class TestGetAffectedIdentityIds:
    """Tests for getting affected identity IDs."""

    async def test_returns_unique_identity_ids(self):
        """Returns set of unique identity IDs."""
        board_id = BoardID()
        identity_id_1 = uuid4()
        identity_id_2 = uuid4()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[identity_id_1, identity_id_2]))
        )
        mock_session.execute = AsyncMock(return_value=mock_result)

        ids = await get_affected_identity_ids(mock_session, board_id, is_test_filter=False)

        assert len(ids) == 2
        assert IdentityID(identity_id_1) in ids
        assert IdentityID(identity_id_2) in ids


@pytest.mark.asyncio
class TestClearBoard:
    """Tests for the main clear_board orchestration function."""

    async def test_dry_run_does_not_delete(self):
        """Dry run mode counts but does not delete."""
        board_id = BoardID()
        account_id = AccountID()
        board = _make_board(board_id=board_id, account_id=account_id)

        mock_session = AsyncMock()
        mock_board_service = MagicMock()
        mock_board_service.get_board_by_short_code = AsyncMock(return_value=board)

        # Mock count results
        mock_count_results = [
            MagicMock(scalar=MagicMock(return_value=100)),  # score_events
            MagicMock(scalar=MagicMock(return_value=5)),  # score_flags
            MagicMock(scalar=MagicMock(return_value=0)),  # run_entries
            MagicMock(scalar=MagicMock(return_value=50)),  # board_states
            MagicMock(scalar=MagicMock(return_value=50)),  # submission_meta
            MagicMock(scalar=MagicMock(return_value=25)),  # affected_identities
        ]
        mock_session.execute = AsyncMock(side_effect=mock_count_results)

        with (
            patch(
                "leadr.common.utils.clear_board.async_session_factory",
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)),
            ),
            patch("leadr.common.utils.clear_board.BoardService", return_value=mock_board_service),
        ):
            # Should not raise and should not call delete
            await clear_board(
                board_input="TESTCODE",
                account_id=str(account_id.uuid),
                mode="production",
                dry_run=True,
            )

        # In dry run mode, we should only count, not delete
        # The execute calls should be only for counting (6 calls)
        assert mock_session.execute.await_count == 6

    async def test_execute_mode_deletes(self):
        """Execute mode deletes records and recomputes."""
        board_id = BoardID()
        account_id = AccountID()
        identity_id_1 = uuid4()
        board = _make_board(board_id=board_id, account_id=account_id)

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_board_service = MagicMock()
        mock_board_service.get_board_by_short_code = AsyncMock(return_value=board)

        mock_flag_service = MagicMock()
        mock_flag_service.recompute_state_for_identities = AsyncMock(return_value=1)

        # Mock results for: count queries + identity query + delete queries
        mock_count_results = [
            MagicMock(scalar=MagicMock(return_value=100)),  # score_events count
            MagicMock(scalar=MagicMock(return_value=5)),  # score_flags count
            MagicMock(scalar=MagicMock(return_value=0)),  # run_entries count
            MagicMock(scalar=MagicMock(return_value=50)),  # board_states count
            MagicMock(scalar=MagicMock(return_value=50)),  # submission_meta count
            MagicMock(scalar=MagicMock(return_value=1)),  # affected_identities count
        ]
        mock_identity_result = MagicMock()
        mock_identity_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[identity_id_1]))
        )
        mock_delete_results = [
            MagicMock(rowcount=5),  # score_flags delete
            MagicMock(rowcount=0),  # run_entries delete
            MagicMock(rowcount=50),  # submission_meta delete
            MagicMock(rowcount=50),  # board_states delete
            MagicMock(rowcount=100),  # score_events delete
        ]

        mock_session.execute = AsyncMock(
            side_effect=mock_count_results + [mock_identity_result] + mock_delete_results
        )

        with (
            patch(
                "leadr.common.utils.clear_board.async_session_factory",
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)),
            ),
            patch("leadr.common.utils.clear_board.BoardService", return_value=mock_board_service),
            patch(
                "leadr.common.utils.clear_board.ScoreFlagService",
                return_value=mock_flag_service,
            ),
        ):
            await clear_board(
                board_input="TESTCODE",
                account_id=str(account_id.uuid),
                mode="production",
                dry_run=False,
            )

        # Should have called delete (5 delete queries + 6 count queries + 1 identity query)
        assert mock_session.execute.await_count == 12
        mock_session.commit.assert_awaited_once()

    async def test_idempotent_on_empty_board(self):
        """Running on empty board succeeds with zero counts."""
        board_id = BoardID()
        account_id = AccountID()
        board = _make_board(board_id=board_id, account_id=account_id)

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_board_service = MagicMock()
        mock_board_service.get_board_by_short_code = AsyncMock(return_value=board)

        # All counts return 0
        mock_count_results = [MagicMock(scalar=MagicMock(return_value=0)) for _ in range(6)]
        mock_identity_result = MagicMock()
        mock_identity_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[]))
        )
        mock_delete_results = [MagicMock(rowcount=0) for _ in range(5)]

        mock_session.execute = AsyncMock(
            side_effect=mock_count_results + [mock_identity_result] + mock_delete_results
        )

        with (
            patch(
                "leadr.common.utils.clear_board.async_session_factory",
                return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session)),
            ),
            patch("leadr.common.utils.clear_board.BoardService", return_value=mock_board_service),
        ):
            # Should not raise
            await clear_board(
                board_input="TESTCODE",
                account_id=str(account_id.uuid),
                mode="production",
                dry_run=False,
            )

        # Should still commit (idempotent)
        mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
class TestRecomputeStateForIdentities:
    """Tests for the recompute_state_for_identities method in ScoreFlagService."""

    async def test_deletes_state_when_no_events_remain(self):
        """When no events remain for identity, deletes BoardState."""
        board_id = BoardID()
        identity_id = IdentityID()
        board = _make_board(board_id=board_id, board_type=BoardType.RUN_IDENTITY)

        mock_session = AsyncMock()

        # Mock count query returning 0 (no events)
        mock_count_result = MagicMock()
        mock_count_result.scalar = MagicMock(return_value=0)
        mock_session.execute = AsyncMock(return_value=mock_count_result)

        service = ScoreFlagService(mock_session)

        recomputed = await service.recompute_state_for_identities(board, {identity_id})

        assert recomputed == 1
        # Should have executed: count query + delete query
        assert mock_session.execute.await_count == 2

    async def test_recomputes_run_identity_board(self):
        """Recomputes RUN_IDENTITY board state when events remain."""
        board_id = BoardID()
        identity_id = IdentityID()
        board = _make_board(board_id=board_id, board_type=BoardType.RUN_IDENTITY)

        mock_session = AsyncMock()

        # Mock count query returning > 0 (events exist)
        mock_count_result = MagicMock()
        mock_count_result.scalar = MagicMock(return_value=5)
        mock_session.execute = AsyncMock(return_value=mock_count_result)

        service = ScoreFlagService(mock_session)
        service._recompute_run_identity = AsyncMock()
        service._sync_ratio_dependents = AsyncMock()

        with patch("leadr.scores.services.score_flag_service.BoardStateService") as mock_state_svc:
            mock_state_svc.return_value.get_by_board_and_identity = AsyncMock(
                return_value=MagicMock()
            )

            recomputed = await service.recompute_state_for_identities(board, {identity_id})

        assert recomputed == 1
        service._recompute_run_identity.assert_awaited_once()
        service._sync_ratio_dependents.assert_awaited_once()

    async def test_recomputes_counter_board(self):
        """Recomputes COUNTER board state when events remain."""
        board_id = BoardID()
        identity_id = IdentityID()
        board = _make_board(board_id=board_id, board_type=BoardType.COUNTER)

        mock_session = AsyncMock()

        mock_count_result = MagicMock()
        mock_count_result.scalar = MagicMock(return_value=5)
        mock_session.execute = AsyncMock(return_value=mock_count_result)

        service = ScoreFlagService(mock_session)
        service._sync_counter_state = AsyncMock()
        service._sync_ratio_dependents = AsyncMock()

        with patch("leadr.scores.services.score_flag_service.BoardStateService") as mock_state_svc:
            mock_state_svc.return_value.get_by_board_and_identity = AsyncMock(
                return_value=MagicMock()
            )

            recomputed = await service.recompute_state_for_identities(board, {identity_id})

        assert recomputed == 1
        service._sync_counter_state.assert_awaited_once()
        service._sync_ratio_dependents.assert_awaited_once()

    async def test_skips_run_runs_board(self):
        """RUN_RUNS boards don't need BoardState recomputation."""
        board_id = BoardID()
        identity_id = IdentityID()
        board = _make_board(board_id=board_id, board_type=BoardType.RUN_RUNS)

        mock_session = AsyncMock()

        # Mock count returning > 0
        mock_count_result = MagicMock()
        mock_count_result.scalar = MagicMock(return_value=5)
        mock_session.execute = AsyncMock(return_value=mock_count_result)

        service = ScoreFlagService(mock_session)
        service._recompute_run_identity = AsyncMock()
        service._sync_counter_state = AsyncMock()
        service._sync_ratio_dependents = AsyncMock()

        with patch("leadr.scores.services.score_flag_service.BoardStateService") as mock_state_svc:
            mock_state_svc.return_value.get_by_board_and_identity = AsyncMock(
                return_value=MagicMock()
            )

            recomputed = await service.recompute_state_for_identities(board, {identity_id})

        # Should still count as recomputed (the identity was processed)
        assert recomputed == 1

        # Should not call recomputation methods for RUN_RUNS
        service._recompute_run_identity.assert_not_awaited()
        service._sync_counter_state.assert_not_awaited()
        # Should not call ratio dependents for RUN_RUNS
        service._sync_ratio_dependents.assert_not_awaited()

    async def test_handles_multiple_identities(self):
        """Processes multiple identities."""
        board = _make_board(board_type=BoardType.RUN_IDENTITY)
        identity_ids = {IdentityID(), IdentityID(), IdentityID()}

        mock_session = AsyncMock()

        # All identities have events
        mock_count_result = MagicMock()
        mock_count_result.scalar = MagicMock(return_value=5)
        mock_session.execute = AsyncMock(return_value=mock_count_result)

        service = ScoreFlagService(mock_session)
        service._recompute_run_identity = AsyncMock()
        service._sync_ratio_dependents = AsyncMock()

        with patch("leadr.scores.services.score_flag_service.BoardStateService") as mock_state_svc:
            mock_state_svc.return_value.get_by_board_and_identity = AsyncMock(
                return_value=MagicMock()
            )

            recomputed = await service.recompute_state_for_identities(board, identity_ids)

        assert recomputed == 3
        assert service._recompute_run_identity.await_count == 3
