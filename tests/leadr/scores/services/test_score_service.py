"""Tests for ScoreService."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from leadr.boards.domain.board import Board, BoardType, KeepStrategy, SortDirection
from leadr.boards.domain.board_ratio_config import BoardRatioConfig
from leadr.boards.domain.board_state import BoardState
from leadr.boards.domain.run_entry import RunEntry
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.exceptions import EntityNotFoundError, PlayerNameConflictError
from leadr.common.domain.ids import (
    AccountID,
    BoardID,
    BoardStateID,
    GameID,
    IdentityID,
    RunEntryID,
    ScoreEventID,
    ScoreID,
)
from leadr.common.domain.pagination import SortDirection as PaginationSortDirection
from leadr.common.domain.pagination_result import PaginatedResult
from leadr.scores.domain.anti_cheat.enums import FlagAction, FlagConfidence, FlagType
from leadr.scores.domain.anti_cheat.models import AntiCheatResult, ScoreSubmissionMeta
from leadr.scores.domain.score_event import ScoreEvent
from leadr.scores.services.score_service import ScoreService


@pytest.mark.asyncio
class TestScoreServiceSubmission:
    """Tests for score submission flow."""

    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.ScoreEventService")
    @patch("leadr.scores.services.score_service.BoardStateService")
    @patch("leadr.scores.services.score_service.settings")
    async def test_submit_score_run_identity_first_submission(
        self,
        mock_settings,
        mock_board_state_service_cls,
        mock_event_service_cls,
        mock_board_service_cls,
    ):
        """Test first submission to a RUN_IDENTITY board creates a BoardState."""
        mock_settings.ANTICHEAT_ENABLED = False

        # Create test domain objects
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="High Scores",
            slug="high-scores",
            short_code="ABC123",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        event = ScoreEvent(
            id=ScoreEventID(),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100.0},
        )

        board_state = BoardState(
            id=BoardStateID(),
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
            player_name="Player1",
        )

        # Configure mocks
        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_event_service = AsyncMock()
        mock_event_service.create_score_event = AsyncMock(return_value=event)
        mock_event_service_cls.return_value = mock_event_service

        mock_state_service = AsyncMock()
        mock_state_service.get_by_board_and_identity = AsyncMock(return_value=None)
        mock_state_service.create_board_state = AsyncMock(return_value=board_state)
        mock_board_state_service_cls.return_value = mock_state_service

        # Test
        mock_session = AsyncMock()
        service = ScoreService(mock_session)
        result_event, result_entry, result_ac = await service.submit_score(
            board_id=board_id,
            identity_id=identity_id,
            value=100.0,
            player_name="Player1",
        )

        assert result_event is not None
        assert result_entry is not None
        assert result_entry.primary_value == 100.0
        assert result_ac is None

        mock_state_service.create_board_state.assert_called_once()

    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.ScoreEventService")
    @patch("leadr.scores.services.score_service.BoardStateService")
    @patch("leadr.scores.services.score_service.settings")
    async def test_submit_score_run_identity_keep_best_higher_is_better(
        self,
        mock_settings,
        mock_board_state_service_cls,
        mock_event_service_cls,
        mock_board_service_cls,
    ):
        """Test BEST strategy keeps higher score for DESCENDING board."""
        mock_settings.ANTICHEAT_ENABLED = False

        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="High Scores",
            slug="high-scores",
            short_code="ABC123",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        # Configure mocks
        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_event_service = AsyncMock()
        mock_event_service_cls.return_value = mock_event_service

        mock_state_service = AsyncMock()
        mock_board_state_service_cls.return_value = mock_state_service

        mock_session = AsyncMock()
        service = ScoreService(mock_session)

        # First submission (100)
        event1 = ScoreEvent(
            id=ScoreEventID(),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100.0},
        )
        state1 = BoardState(
            id=BoardStateID(),
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
            player_name="Player1",
        )
        mock_event_service.create_score_event = AsyncMock(return_value=event1)
        mock_state_service.get_by_board_and_identity = AsyncMock(return_value=None)
        mock_state_service.create_board_state = AsyncMock(return_value=state1)

        _, entry1, _ = await service.submit_score(
            board_id=board_id,
            identity_id=identity_id,
            value=100.0,
            player_name="Player1",
        )
        assert entry1 is not None
        assert entry1.primary_value == 100.0

        # Second submission (200, better)
        event2 = ScoreEvent(
            id=ScoreEventID(),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 200.0},
        )
        state2 = BoardState(
            id=BoardStateID(),
            board_id=board_id,
            identity_id=identity_id,
            primary_value=200.0,
            player_name="Player1",
        )
        mock_event_service.create_score_event = AsyncMock(return_value=event2)
        mock_state_service.get_by_board_and_identity = AsyncMock(return_value=state1)
        mock_state_service.upsert_board_state = AsyncMock(return_value=state2)

        _, entry2, _ = await service.submit_score(
            board_id=board_id,
            identity_id=identity_id,
            value=200.0,
            player_name="Player1",
        )
        assert entry2 is not None
        assert entry2.primary_value == 200.0

        # Third submission (150, worse)
        event3 = ScoreEvent(
            id=ScoreEventID(),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 150.0},
        )
        state3 = BoardState(
            id=BoardStateID(),
            board_id=board_id,
            identity_id=identity_id,
            primary_value=200.0,  # Still 200
            player_name="Player1",
        )
        mock_event_service.create_score_event = AsyncMock(return_value=event3)
        mock_state_service.get_by_board_and_identity = AsyncMock(return_value=state2)
        mock_state_service.upsert_board_state = AsyncMock(return_value=state3)

        _, entry3, _ = await service.submit_score(
            board_id=board_id,
            identity_id=identity_id,
            value=150.0,
            player_name="Player1",
        )
        assert entry3 is not None
        assert entry3.primary_value == 200.0

    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.ScoreEventService")
    @patch("leadr.scores.services.score_service.BoardStateService")
    @patch("leadr.scores.services.score_service.settings")
    async def test_submit_score_run_identity_keep_best_lower_is_better(
        self,
        mock_settings,
        mock_board_state_service_cls,
        mock_event_service_cls,
        mock_board_service_cls,
    ):
        """Test BEST strategy keeps lower score for ASCENDING board."""
        mock_settings.ANTICHEAT_ENABLED = False

        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speedruns",
            slug="speedruns",
            short_code="SPD001",
            sort_direction=SortDirection.ASCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_event_service = AsyncMock()
        mock_event_service_cls.return_value = mock_event_service

        mock_state_service = AsyncMock()
        mock_board_state_service_cls.return_value = mock_state_service

        mock_session = AsyncMock()
        service = ScoreService(mock_session)

        # First: 120
        event1 = ScoreEvent(
            id=ScoreEventID(),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 120.0},
        )
        state1 = BoardState(
            id=BoardStateID(),
            board_id=board_id,
            identity_id=identity_id,
            primary_value=120.0,
            player_name="Speedrunner",
        )
        mock_event_service.create_score_event = AsyncMock(return_value=event1)
        mock_state_service.get_by_board_and_identity = AsyncMock(return_value=None)
        mock_state_service.create_board_state = AsyncMock(return_value=state1)

        _, entry1, _ = await service.submit_score(
            board_id=board_id,
            identity_id=identity_id,
            value=120.0,
            player_name="Speedrunner",
        )
        assert entry1 is not None
        assert entry1.primary_value == 120.0

        # Second: 100 (better)
        event2 = ScoreEvent(
            id=ScoreEventID(),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100.0},
        )
        state2 = BoardState(
            id=BoardStateID(),
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
            player_name="Speedrunner",
        )
        mock_event_service.create_score_event = AsyncMock(return_value=event2)
        mock_state_service.get_by_board_and_identity = AsyncMock(return_value=state1)
        mock_state_service.upsert_board_state = AsyncMock(return_value=state2)

        _, entry2, _ = await service.submit_score(
            board_id=board_id,
            identity_id=identity_id,
            value=100.0,
            player_name="Speedrunner",
        )
        assert entry2 is not None
        assert entry2.primary_value == 100.0

        # Third: 110 (worse)
        event3 = ScoreEvent(
            id=ScoreEventID(),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 110.0},
        )
        state3 = BoardState(
            id=BoardStateID(),
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,  # Still 100
            player_name="Speedrunner",
        )
        mock_event_service.create_score_event = AsyncMock(return_value=event3)
        mock_state_service.get_by_board_and_identity = AsyncMock(return_value=state2)
        mock_state_service.upsert_board_state = AsyncMock(return_value=state3)

        _, entry3, _ = await service.submit_score(
            board_id=board_id,
            identity_id=identity_id,
            value=110.0,
            player_name="Speedrunner",
        )
        assert entry3 is not None
        assert entry3.primary_value == 100.0

    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.ScoreEventService")
    @patch("leadr.scores.services.score_service.BoardStateService")
    @patch("leadr.scores.services.score_service.settings")
    async def test_submit_score_run_identity_keep_first(
        self,
        mock_settings,
        mock_board_state_service_cls,
        mock_event_service_cls,
        mock_board_service_cls,
    ):
        """Test FIRST strategy keeps the first score."""
        mock_settings.ANTICHEAT_ENABLED = False

        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="First Completion",
            slug="first-completion",
            short_code="FST001",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.FIRST,
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_event_service = AsyncMock()
        mock_event_service_cls.return_value = mock_event_service

        mock_state_service = AsyncMock()
        mock_board_state_service_cls.return_value = mock_state_service

        mock_session = AsyncMock()
        service = ScoreService(mock_session)

        # First: 100
        event1 = ScoreEvent(
            id=ScoreEventID(),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100.0},
        )
        state1 = BoardState(
            id=BoardStateID(),
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
            player_name="Player1",
        )
        mock_event_service.create_score_event = AsyncMock(return_value=event1)
        mock_state_service.get_by_board_and_identity = AsyncMock(return_value=None)
        mock_state_service.create_board_state = AsyncMock(return_value=state1)

        _, entry1, _ = await service.submit_score(
            board_id=board_id,
            identity_id=identity_id,
            value=100.0,
            player_name="Player1",
        )
        assert entry1 is not None
        assert entry1.primary_value == 100.0

        # Second: 200 (ignored)
        event2 = ScoreEvent(
            id=ScoreEventID(),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 200.0},
        )
        state2 = BoardState(
            id=BoardStateID(),
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,  # Still 100
            player_name="Player1",
        )
        mock_event_service.create_score_event = AsyncMock(return_value=event2)
        mock_state_service.get_by_board_and_identity = AsyncMock(return_value=state1)
        mock_state_service.upsert_board_state = AsyncMock(return_value=state2)

        _, entry2, _ = await service.submit_score(
            board_id=board_id,
            identity_id=identity_id,
            value=200.0,
            player_name="Player1",
        )
        assert entry2 is not None
        assert entry2.primary_value == 100.0

    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.ScoreEventService")
    @patch("leadr.scores.services.score_service.BoardStateService")
    @patch("leadr.scores.services.score_service.settings")
    async def test_submit_score_run_identity_keep_latest(
        self,
        mock_settings,
        mock_board_state_service_cls,
        mock_event_service_cls,
        mock_board_service_cls,
    ):
        """Test LATEST strategy always uses the latest score."""
        mock_settings.ANTICHEAT_ENABLED = False

        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Latest Score",
            slug="latest-score",
            short_code="LTS001",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.LATEST,
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_event_service = AsyncMock()
        mock_event_service_cls.return_value = mock_event_service

        mock_state_service = AsyncMock()
        mock_board_state_service_cls.return_value = mock_state_service

        mock_session = AsyncMock()
        service = ScoreService(mock_session)

        # First: 100
        event1 = ScoreEvent(
            id=ScoreEventID(),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100.0},
        )
        state1 = BoardState(
            id=BoardStateID(),
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
            player_name="Player1",
        )
        mock_event_service.create_score_event = AsyncMock(return_value=event1)
        mock_state_service.get_by_board_and_identity = AsyncMock(return_value=None)
        mock_state_service.create_board_state = AsyncMock(return_value=state1)

        _, entry1, _ = await service.submit_score(
            board_id=board_id,
            identity_id=identity_id,
            value=100.0,
            player_name="Player1",
        )
        assert entry1 is not None
        assert entry1.primary_value == 100.0

        # Second: 50 (latest, even though lower)
        event2 = ScoreEvent(
            id=ScoreEventID(),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 50.0},
        )
        state2 = BoardState(
            id=BoardStateID(),
            board_id=board_id,
            identity_id=identity_id,
            primary_value=50.0,  # Updated to latest
            player_name="Player1",
        )
        mock_event_service.create_score_event = AsyncMock(return_value=event2)
        mock_state_service.get_by_board_and_identity = AsyncMock(return_value=state1)
        mock_state_service.upsert_board_state = AsyncMock(return_value=state2)

        _, entry2, _ = await service.submit_score(
            board_id=board_id,
            identity_id=identity_id,
            value=50.0,
            player_name="Player1",
        )
        assert entry2 is not None
        assert entry2.primary_value == 50.0

    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.ScoreEventService")
    @patch("leadr.scores.services.score_service.RunEntryService")
    @patch("leadr.scores.services.score_service.settings")
    async def test_submit_score_run_runs_creates_entry(
        self,
        mock_settings,
        mock_run_entry_service_cls,
        mock_event_service_cls,
        mock_board_service_cls,
    ):
        """Test RUN_RUNS board creates a new RunEntry for each submission."""
        mock_settings.ANTICHEAT_ENABLED = False

        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speedruns",
            slug="speedruns",
            short_code="SPD001",
            sort_direction=SortDirection.ASCENDING,
            board_type=BoardType.RUN_RUNS,
            keep_strategy=KeepStrategy.NA,
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_event_service = AsyncMock()
        mock_event_service_cls.return_value = mock_event_service

        mock_run_service = AsyncMock()
        mock_run_entry_service_cls.return_value = mock_run_service

        mock_session = AsyncMock()
        service = ScoreService(mock_session)

        # First submission
        event1 = ScoreEvent(
            id=ScoreEventID(),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 120.0},
        )
        entry1 = RunEntry(
            id=RunEntryID(),
            board_id=board_id,
            identity_id=identity_id,
            score_event_id=event1.id,
            primary_value=120.0,
            player_name="Speedrunner",
        )
        mock_event_service.create_score_event = AsyncMock(return_value=event1)
        mock_run_service.create_run_entry = AsyncMock(return_value=entry1)

        _, result1, _ = await service.submit_score(
            board_id=board_id,
            identity_id=identity_id,
            value=120.0,
            player_name="Speedrunner",
        )

        # Second submission
        event2 = ScoreEvent(
            id=ScoreEventID(),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 110.0},
        )
        entry2 = RunEntry(
            id=RunEntryID(),
            board_id=board_id,
            identity_id=identity_id,
            score_event_id=event2.id,
            primary_value=110.0,
            player_name="Speedrunner",
        )
        mock_event_service.create_score_event = AsyncMock(return_value=event2)
        mock_run_service.create_run_entry = AsyncMock(return_value=entry2)

        _, result2, _ = await service.submit_score(
            board_id=board_id,
            identity_id=identity_id,
            value=110.0,
            player_name="Speedrunner",
        )

        # Each submission should create a new entry
        assert result1 is not None
        assert result2 is not None
        assert result1.id != result2.id
        assert result1.primary_value == 120.0
        assert result2.primary_value == 110.0

    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.ScoreEventService")
    @patch("leadr.scores.services.score_service.BoardStateService")
    @patch("leadr.scores.services.score_service.settings")
    async def test_submit_score_counter_accumulates(
        self,
        mock_settings,
        mock_board_state_service_cls,
        mock_event_service_cls,
        mock_board_service_cls,
    ):
        """Test COUNTER board accumulates delta values."""
        mock_settings.ANTICHEAT_ENABLED = False

        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Kill Count",
            slug="kill-count",
            short_code="KIL001",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.COUNTER,
            keep_strategy=KeepStrategy.NA,
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_event_service = AsyncMock()
        mock_event_service_cls.return_value = mock_event_service

        mock_state_service = AsyncMock()
        mock_board_state_service_cls.return_value = mock_state_service

        mock_session = AsyncMock()
        service = ScoreService(mock_session)

        # First delta: 5
        event1 = ScoreEvent(
            id=ScoreEventID(),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"delta": 5.0},
        )
        state1 = BoardState(
            id=BoardStateID(),
            board_id=board_id,
            identity_id=identity_id,
            primary_value=5.0,
            player_name="Killer",
        )
        mock_event_service.create_score_event = AsyncMock(return_value=event1)
        mock_state_service.get_by_board_and_identity = AsyncMock(return_value=None)
        mock_state_service.create_board_state = AsyncMock(return_value=state1)

        _, entry1, _ = await service.submit_score(
            board_id=board_id,
            identity_id=identity_id,
            delta=5.0,
            player_name="Killer",
        )
        assert entry1 is not None
        assert entry1.primary_value == 5.0

        # Second delta: +3 = 8
        event2 = ScoreEvent(
            id=ScoreEventID(),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"delta": 3.0},
        )
        state2 = BoardState(
            id=BoardStateID(),
            board_id=board_id,
            identity_id=identity_id,
            primary_value=8.0,
            player_name="Killer",
        )
        mock_event_service.create_score_event = AsyncMock(return_value=event2)
        mock_state_service.get_by_board_and_identity = AsyncMock(return_value=state1)
        mock_state_service.upsert_board_state = AsyncMock(return_value=state2)

        _, entry2, _ = await service.submit_score(
            board_id=board_id,
            identity_id=identity_id,
            delta=3.0,
            player_name="Killer",
        )
        assert entry2 is not None
        assert entry2.primary_value == 8.0

        # Third delta: -2 = 6
        event3 = ScoreEvent(
            id=ScoreEventID(),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"delta": -2.0},
        )
        state3 = BoardState(
            id=BoardStateID(),
            board_id=board_id,
            identity_id=identity_id,
            primary_value=6.0,
            player_name="Killer",
        )
        mock_event_service.create_score_event = AsyncMock(return_value=event3)
        mock_state_service.get_by_board_and_identity = AsyncMock(return_value=state2)
        mock_state_service.upsert_board_state = AsyncMock(return_value=state3)

        _, entry3, _ = await service.submit_score(
            board_id=board_id,
            identity_id=identity_id,
            delta=-2.0,
            player_name="Killer",
        )
        assert entry3 is not None
        assert entry3.primary_value == 6.0

    @patch("leadr.scores.services.score_service.BoardService")
    async def test_submit_score_ratio_board_rejected(self, mock_board_service_cls):
        """Test that RATIO boards reject direct submissions."""
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="K/D Ratio",
            slug="kd-ratio",
            short_code="KDR001",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RATIO,
            keep_strategy=KeepStrategy.NA,
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_session = AsyncMock()
        service = ScoreService(mock_session)

        with pytest.raises(ValueError, match="RATIO boards do not accept direct submissions"):
            await service.submit_score(
                board_id=board_id,
                identity_id=identity_id,
                value=1.5,
                player_name="Player1",
            )

    @patch("leadr.scores.services.score_service.BoardService")
    async def test_submit_score_missing_value_for_run_board(self, mock_board_service_cls):
        """Test that RUN boards require value."""
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="High Scores",
            slug="high-scores",
            short_code="ABC123",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_session = AsyncMock()
        service = ScoreService(mock_session)

        with pytest.raises(ValueError, match="value is required"):
            await service.submit_score(
                board_id=board_id,
                identity_id=identity_id,
                delta=100.0,  # Wrong param
                player_name="Player1",
            )

    @patch("leadr.scores.services.score_service.BoardService")
    async def test_submit_score_missing_delta_for_counter(self, mock_board_service_cls):
        """Test that COUNTER boards require delta."""
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Kill Count",
            slug="kill-count",
            short_code="KIL001",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.COUNTER,
            keep_strategy=KeepStrategy.NA,
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_session = AsyncMock()
        service = ScoreService(mock_session)

        with pytest.raises(ValueError, match="delta is required"):
            await service.submit_score(
                board_id=board_id,
                identity_id=identity_id,
                value=100.0,  # Wrong param
                player_name="Player1",
            )

    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.ScoreEventService")
    @patch("leadr.scores.services.score_service.BoardStateService")
    @patch("leadr.scores.services.score_service.settings")
    async def test_submit_score_skips_anticheat_when_disabled(
        self,
        mock_settings,
        mock_board_state_service_cls,
        mock_event_service_cls,
        mock_board_service_cls,
    ):
        """Test that anti-cheat is skipped when ANTICHEAT_ENABLED is False."""
        mock_settings.ANTICHEAT_ENABLED = False

        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="High Scores",
            slug="high-scores",
            short_code="ABC123",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        event = ScoreEvent(
            id=ScoreEventID(),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100.0},
        )

        state = BoardState(
            id=BoardStateID(),
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
            player_name="Player1",
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_event_service = AsyncMock()
        mock_event_service.create_score_event = AsyncMock(return_value=event)
        mock_event_service_cls.return_value = mock_event_service

        mock_state_service = AsyncMock()
        mock_state_service.get_by_board_and_identity = AsyncMock(return_value=None)
        mock_state_service.create_board_state = AsyncMock(return_value=state)
        mock_board_state_service_cls.return_value = mock_state_service

        mock_session = AsyncMock()
        service = ScoreService(mock_session)

        result_event, result_entry, result_ac = await service.submit_score(
            board_id=board_id,
            identity_id=identity_id,
            value=100.0,
            player_name="Player1",
        )

        assert result_event is not None
        assert result_entry is not None
        assert result_entry.primary_value == 100.0
        assert result_ac is None

    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.ScoreEventService")
    @patch("leadr.scores.services.score_service.BoardStateService")
    @patch("leadr.scores.services.score_service.AntiCheatService")
    @patch("leadr.scores.services.score_service.ScoreSubmissionMetaRepository")
    @patch("leadr.scores.services.score_service.settings")
    async def test_submit_score_runs_anticheat_when_enabled(
        self,
        mock_settings,
        mock_meta_repo_cls,
        mock_ac_service_cls,
        mock_board_state_service_cls,
        mock_event_service_cls,
        mock_board_service_cls,
    ):
        """Test that anti-cheat runs when ANTICHEAT_ENABLED is True."""
        mock_settings.ANTICHEAT_ENABLED = True

        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="High Scores",
            slug="high-scores",
            short_code="ABC123",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        event = ScoreEvent(
            id=ScoreEventID(),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100.0},
        )

        state = BoardState(
            id=BoardStateID(),
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
            player_name="Player1",
        )

        ac_result = AntiCheatResult(
            action=FlagAction.ACCEPT,
            flag_type=None,
            confidence=None,
            metadata={},
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_event_service = AsyncMock()
        mock_event_service.create_score_event = AsyncMock(return_value=event)
        mock_event_service_cls.return_value = mock_event_service

        mock_state_service = AsyncMock()
        mock_state_service.get_by_board_and_identity = AsyncMock(return_value=None)
        mock_state_service.create_board_state = AsyncMock(return_value=state)
        mock_board_state_service_cls.return_value = mock_state_service

        mock_ac_service = AsyncMock()
        mock_ac_service.check_submission_for_event = AsyncMock(return_value=ac_result)
        mock_ac_service_cls.return_value = mock_ac_service

        mock_meta_repo = AsyncMock()
        mock_meta_repo.get_by_identity_and_board = AsyncMock(return_value=None)
        mock_meta_repo.create = AsyncMock()
        mock_meta_repo_cls.return_value = mock_meta_repo

        mock_session = AsyncMock()
        service = ScoreService(mock_session)

        result_event, result_entry, result_ac = await service.submit_score(
            board_id=board_id,
            identity_id=identity_id,
            value=100.0,
            player_name="Player1",
        )

        assert result_event is not None
        assert result_entry is not None
        assert result_ac is not None
        mock_ac_service.check_submission_for_event.assert_called_once()

    @patch("leadr.scores.services.score_service.BoardService")
    async def test_submit_score_board_not_found(self, mock_board_service_cls):
        """Test submitting to non-existent board raises error."""
        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(
            side_effect=EntityNotFoundError("Board", "fake-id")
        )
        mock_board_service_cls.return_value = mock_board_service

        mock_session = AsyncMock()
        service = ScoreService(mock_session)

        fake_board_id = BoardID()
        identity_id = IdentityID()

        with pytest.raises(EntityNotFoundError):
            await service.submit_score(
                board_id=fake_board_id,
                identity_id=identity_id,
                value=100.0,
                player_name="Player1",
            )

    @patch("leadr.scores.services.score_service.BoardStateRepository")
    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.ScoreEventService")
    @patch("leadr.scores.services.score_service.BoardStateService")
    @patch("leadr.scores.services.score_service.settings")
    async def test_submit_score_checks_unique_player_name(
        self,
        mock_settings,
        mock_board_state_service_cls,
        mock_event_service_cls,
        mock_board_service_cls,
        mock_board_state_repo_cls,
    ):
        """Test submission checks player name uniqueness when enabled."""
        mock_settings.ANTICHEAT_ENABLED = False
        board_id = BoardID()
        identity_id = IdentityID()

        board = Board(
            id=board_id,
            account_id=AccountID(),
            game_id=GameID(),
            name="High Scores",
            slug="high-scores",
            short_code="ABC123",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
            unique_player_names=True,
        )

        event = ScoreEvent(
            id=ScoreEventID(),
            account_id=board.account_id,
            game_id=board.game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100.0},
        )

        state = BoardState(
            id=BoardStateID(),
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
            player_name="Player One",
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_repo = AsyncMock()
        mock_repo.is_player_name_available = AsyncMock(return_value=True)
        mock_board_state_repo_cls.return_value = mock_repo

        mock_event_service = AsyncMock()
        mock_event_service.create_score_event = AsyncMock(return_value=event)
        mock_event_service_cls.return_value = mock_event_service

        mock_state_service = AsyncMock()
        mock_state_service.get_by_board_and_identity = AsyncMock(return_value=None)
        mock_state_service.create_board_state = AsyncMock(return_value=state)
        mock_board_state_service_cls.return_value = mock_state_service

        service = ScoreService(AsyncMock())
        result_event, result_entry, _ = await service.submit_score(
            board_id=board_id,
            identity_id=identity_id,
            value=100.0,
            player_name="Player One",
        )

        assert result_event is not None
        assert result_entry is not None
        mock_repo.is_player_name_available.assert_called_once_with(
            board_id=board_id,
            player_name="player one",
            exclude_identity_id=identity_id,
        )

    @patch("leadr.scores.services.score_service.BoardStateRepository")
    @patch("leadr.scores.services.score_service.BoardService")
    async def test_submit_score_unique_name_conflict_raises(
        self,
        mock_board_service_cls,
        mock_board_state_repo_cls,
    ):
        """Test that a taken player name raises PlayerNameConflictError."""
        board_id = BoardID()
        identity_id = IdentityID()

        board = Board(
            id=board_id,
            account_id=AccountID(),
            game_id=GameID(),
            name="High Scores",
            slug="high-scores",
            short_code="ABC123",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
            unique_player_names=True,
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_repo = AsyncMock()
        mock_repo.is_player_name_available = AsyncMock(return_value=False)
        mock_board_state_repo_cls.return_value = mock_repo

        service = ScoreService(AsyncMock())

        with pytest.raises(PlayerNameConflictError):
            await service.submit_score(
                board_id=board_id,
                identity_id=identity_id,
                value=100.0,
                player_name="Taken Name",
            )

    @patch("leadr.scores.services.score_service.RunEntryRepository")
    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.ScoreEventService")
    @patch("leadr.scores.services.score_service.RunEntryService")
    @patch("leadr.scores.services.score_service.settings")
    async def test_submit_score_unique_name_run_runs_board(
        self,
        mock_settings,
        mock_run_entry_service_cls,
        mock_event_service_cls,
        mock_board_service_cls,
        mock_run_entry_repo_cls,
    ):
        """Test unique name check uses RunEntryRepository for RUN_RUNS boards."""
        mock_settings.ANTICHEAT_ENABLED = False
        board_id = BoardID()
        identity_id = IdentityID()

        board = Board(
            id=board_id,
            account_id=AccountID(),
            game_id=GameID(),
            name="Speedruns",
            slug="speedruns",
            short_code="SPD001",
            sort_direction=SortDirection.ASCENDING,
            board_type=BoardType.RUN_RUNS,
            keep_strategy=KeepStrategy.NA,
            unique_player_names=True,
        )

        event = ScoreEvent(
            id=ScoreEventID(),
            account_id=board.account_id,
            game_id=board.game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 50.0},
        )

        entry = RunEntry(
            id=RunEntryID(),
            board_id=board_id,
            identity_id=identity_id,
            score_event_id=event.id,
            primary_value=50.0,
            player_name="Runner",
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_repo = AsyncMock()
        mock_repo.is_player_name_available = AsyncMock(return_value=True)
        mock_run_entry_repo_cls.return_value = mock_repo

        mock_event_service = AsyncMock()
        mock_event_service.create_score_event = AsyncMock(return_value=event)
        mock_event_service_cls.return_value = mock_event_service

        mock_run_service = AsyncMock()
        mock_run_service.create_run_entry = AsyncMock(return_value=entry)
        mock_run_entry_service_cls.return_value = mock_run_service

        service = ScoreService(AsyncMock())
        await service.submit_score(
            board_id=board_id,
            identity_id=identity_id,
            value=50.0,
            player_name="Runner",
        )

        mock_repo.is_player_name_available.assert_called_once()

    @patch("leadr.scores.services.score_service.BoardService")
    async def test_submit_score_unique_name_empty_skips_check(
        self,
        mock_board_service_cls,
    ):
        """Test that whitespace-only player name skips uniqueness check."""
        board_id = BoardID()

        board = Board(
            id=board_id,
            account_id=AccountID(),
            game_id=GameID(),
            name="High Scores",
            slug="high-scores",
            short_code="ABC123",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
            unique_player_names=True,
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        service = ScoreService(AsyncMock())

        # Whitespace-only name normalises to empty → but submit_score checks
        # `if board.unique_player_names and player_name` — empty string is falsy,
        # so the uniqueness check is skipped entirely at line 150.
        # Use a non-empty name but with only whitespace to test the normalisation path.
        # Actually, "   " is truthy, so it enters _check_player_name_availability,
        # which normalises to "" and returns early (line 302-303).
        # We need to also patch ScoreEventService to avoid the event creation.
        # But the check happens BEFORE event creation, so we can just verify no error.
        # Actually line 150: `if board.unique_player_names and player_name:` —
        # "   " is truthy, so it WILL enter the check. Good — this covers lines 301-303.
        # But after the check, it continues to event creation which needs mocking.
        # Simplest: test _check_player_name_availability directly.
        await service._check_player_name_availability(board, IdentityID(), "   ")
        # If it reaches here without error, the empty-after-normalisation path worked.

    @patch("leadr.scores.services.score_service.ScoreFlagRepository")
    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.ScoreEventService")
    @patch("leadr.scores.services.score_service.BoardStateService")
    @patch("leadr.scores.services.score_service.AntiCheatService")
    @patch("leadr.scores.services.score_service.ScoreSubmissionMetaRepository")
    @patch("leadr.scores.services.score_service.settings")
    async def test_submit_score_anticheat_flag_creates_flag_and_updates_ranking(
        self,
        mock_settings,
        mock_meta_repo_cls,
        mock_ac_service_cls,
        mock_board_state_service_cls,
        mock_event_service_cls,
        mock_board_service_cls,
        mock_flag_repo_cls,
    ):
        """Test anti-cheat FLAG creates a flag but still updates rankings."""
        mock_settings.ANTICHEAT_ENABLED = True
        board_id = BoardID()
        identity_id = IdentityID()

        board = Board(
            id=board_id,
            account_id=AccountID(),
            game_id=GameID(),
            name="High Scores",
            slug="high-scores",
            short_code="ABC123",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        event = ScoreEvent(
            id=ScoreEventID(),
            account_id=board.account_id,
            game_id=board.game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100.0},
        )

        state = BoardState(
            id=BoardStateID(),
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
            player_name="Player1",
        )

        ac_result = AntiCheatResult(
            action=FlagAction.FLAG,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.MEDIUM,
            reason="Submissions too fast",
            metadata={"interval_ms": 500},
        )

        # Existing submission metadata to test update path (lines 669-673)
        existing_meta = ScoreSubmissionMeta(
            score_event_id=ScoreEventID(),
            identity_id=identity_id,
            board_id=board_id,
            submission_count=3,
            last_submission_at=event.created_at,
            last_score_value=90.0,
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_event_service = AsyncMock()
        mock_event_service.create_score_event = AsyncMock(return_value=event)
        mock_event_service_cls.return_value = mock_event_service

        mock_state_service = AsyncMock()
        mock_state_service.get_by_board_and_identity = AsyncMock(return_value=None)
        mock_state_service.create_board_state = AsyncMock(return_value=state)
        mock_board_state_service_cls.return_value = mock_state_service

        mock_ac_service = AsyncMock()
        mock_ac_service.check_submission_for_event = AsyncMock(return_value=ac_result)
        mock_ac_service_cls.return_value = mock_ac_service

        mock_meta_repo = AsyncMock()
        mock_meta_repo.get_by_identity_and_board = AsyncMock(return_value=existing_meta)
        mock_meta_repo.update = AsyncMock()
        mock_meta_repo_cls.return_value = mock_meta_repo

        mock_flag_repo = AsyncMock()
        mock_flag_repo.create = AsyncMock()
        mock_flag_repo_cls.return_value = mock_flag_repo

        service = ScoreService(AsyncMock())
        result_event, result_entry, result_ac = await service.submit_score(
            board_id=board_id,
            identity_id=identity_id,
            value=100.0,
            player_name="Player1",
        )

        # FLAG still produces a ranking entry
        assert result_entry is not None
        assert result_ac is not None
        assert result_ac.action == FlagAction.FLAG

        # Flag was created
        mock_flag_repo.create.assert_called_once()

        # Existing metadata was updated (not created)
        mock_meta_repo.update.assert_called_once()
        assert existing_meta.submission_count == 4

    @patch("leadr.scores.services.score_service.ScoreFlagRepository")
    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.ScoreEventService")
    @patch("leadr.scores.services.score_service.AntiCheatService")
    @patch("leadr.scores.services.score_service.ScoreSubmissionMetaRepository")
    @patch("leadr.scores.services.score_service.settings")
    async def test_submit_score_anticheat_reject_skips_ranking(
        self,
        mock_settings,
        mock_meta_repo_cls,
        mock_ac_service_cls,
        mock_event_service_cls,
        mock_board_service_cls,
        mock_flag_repo_cls,
    ):
        """Test anti-cheat REJECT returns early without updating rankings."""
        mock_settings.ANTICHEAT_ENABLED = True
        board_id = BoardID()
        identity_id = IdentityID()

        board = Board(
            id=board_id,
            account_id=AccountID(),
            game_id=GameID(),
            name="High Scores",
            slug="high-scores",
            short_code="ABC123",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        event = ScoreEvent(
            id=ScoreEventID(),
            account_id=board.account_id,
            game_id=board.game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100.0},
        )

        ac_result = AntiCheatResult(
            action=FlagAction.REJECT,
            flag_type=FlagType.VELOCITY,
            confidence=FlagConfidence.HIGH,
            reason="Too fast",
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_event_service = AsyncMock()
        mock_event_service.create_score_event = AsyncMock(return_value=event)
        mock_event_service_cls.return_value = mock_event_service

        mock_ac_service = AsyncMock()
        mock_ac_service.check_submission_for_event = AsyncMock(return_value=ac_result)
        mock_ac_service_cls.return_value = mock_ac_service

        mock_meta_repo = AsyncMock()
        mock_meta_repo.get_by_identity_and_board = AsyncMock(return_value=None)
        mock_meta_repo.create = AsyncMock()
        mock_meta_repo_cls.return_value = mock_meta_repo

        mock_flag_repo = AsyncMock()
        mock_flag_repo_cls.return_value = mock_flag_repo

        service = ScoreService(AsyncMock())
        result_event, result_entry, result_ac = await service.submit_score(
            board_id=board_id,
            identity_id=identity_id,
            value=100.0,
            player_name="Player1",
        )

        # REJECT returns no ranking entry
        assert result_entry is None
        assert result_ac is not None
        assert result_ac.action == FlagAction.REJECT


@pytest.mark.asyncio
class TestScoreServiceQuery:
    """Tests for score query methods."""

    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.BoardStateService")
    @patch("leadr.scores.services.score_service.BoardStateRepository")
    async def test_get_score_by_id_board_state(
        self, mock_repo_cls, mock_state_service_cls, mock_board_service_cls
    ):
        """Test getting a BoardState score by ID."""
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()
        state_id = BoardStateID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="High Scores",
            slug="high-scores",
            short_code="ABC123",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        state = BoardState(
            id=state_id,
            board_id=board_id,
            identity_id=identity_id,
            primary_value=500.0,
            player_name="Player1",
        )

        mock_state_service = AsyncMock()
        mock_state_service.get_board_state = AsyncMock(return_value=state)
        mock_state_service_cls.return_value = mock_state_service

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_repo = AsyncMock()
        mock_repo.get_rank = AsyncMock(return_value=1)
        mock_repo_cls.return_value = mock_repo

        mock_session = AsyncMock()
        service = ScoreService(mock_session)

        score_id = ScoreID(state_id.uuid)
        result, result_board, rank = await service.get_score_by_id(score_id)

        assert result.id == state.id
        assert result.primary_value == 500.0
        assert result_board.id == board.id
        assert rank == 1

    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.BoardStateService")
    @patch("leadr.scores.services.score_service.RunEntryService")
    @patch("leadr.scores.services.score_service.RunEntryRepository")
    async def test_get_score_by_id_run_entry(
        self,
        mock_repo_cls,
        mock_run_service_cls,
        mock_state_service_cls,
        mock_board_service_cls,
    ):
        """Test getting a RunEntry score by ID."""
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()
        entry_id = RunEntryID()
        event_id = ScoreEventID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speedruns",
            slug="speedruns",
            short_code="SPD001",
            sort_direction=SortDirection.ASCENDING,
            board_type=BoardType.RUN_RUNS,
            keep_strategy=KeepStrategy.NA,
        )

        entry = RunEntry(
            id=entry_id,
            board_id=board_id,
            identity_id=identity_id,
            score_event_id=event_id,
            primary_value=120.0,
            player_name="Speedrunner",
        )

        mock_state_service = AsyncMock()
        mock_state_service.get_board_state = AsyncMock(return_value=None)
        mock_state_service_cls.return_value = mock_state_service

        mock_run_service = AsyncMock()
        mock_run_service.get_run_entry = AsyncMock(return_value=entry)
        mock_run_service_cls.return_value = mock_run_service

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_repo = AsyncMock()
        mock_repo.get_rank = AsyncMock(return_value=1)
        mock_repo_cls.return_value = mock_repo

        mock_session = AsyncMock()
        service = ScoreService(mock_session)

        score_id = ScoreID(entry_id.uuid)
        result, result_board, rank = await service.get_score_by_id(score_id)

        assert result.id == entry.id
        assert result.primary_value == 120.0
        assert result_board.id == board.id

    @patch("leadr.scores.services.score_service.BoardStateService")
    @patch("leadr.scores.services.score_service.RunEntryService")
    async def test_get_score_by_id_not_found(self, mock_run_service_cls, mock_state_service_cls):
        """Test getting non-existent score raises error."""
        mock_state_service = AsyncMock()
        mock_state_service.get_board_state = AsyncMock(return_value=None)
        mock_state_service_cls.return_value = mock_state_service

        mock_run_service = AsyncMock()
        mock_run_service.get_run_entry = AsyncMock(return_value=None)
        mock_run_service_cls.return_value = mock_run_service

        mock_session = AsyncMock()
        service = ScoreService(mock_session)

        fake_id = ScoreID()

        with pytest.raises(EntityNotFoundError):
            await service.get_score_by_id(fake_id)

    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.BoardStateService")
    async def test_list_scores_board_state(self, mock_state_service_cls, mock_board_service_cls):
        """Test listing scores from a RUN_IDENTITY board."""
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="High Scores",
            slug="high-scores",
            short_code="ABC123",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        states = [
            BoardState(
                id=BoardStateID(),
                board_id=board_id,
                identity_id=IdentityID(),
                primary_value=float(i * 100),
                player_name=f"Player{i}",
            )
            for i in range(5)
        ]

        paginated = PaginatedResult(
            items=states,
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_state_service = AsyncMock()
        mock_state_service.list_board_states = AsyncMock(return_value=paginated)
        mock_state_service_cls.return_value = mock_state_service

        mock_session = AsyncMock()
        service = ScoreService(mock_session)

        pagination = PaginationParams(limit=10, cursor=None, sort=None)
        result = await service.list_scores(
            board_id=board_id,
            pagination=pagination,
        )

        assert len(result.items) == 5

    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.RunEntryService")
    async def test_list_scores_run_entry(self, mock_run_service_cls, mock_board_service_cls):
        """Test listing scores from a RUN_RUNS board."""
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Speedruns",
            slug="speedruns",
            short_code="SPD001",
            sort_direction=SortDirection.ASCENDING,
            board_type=BoardType.RUN_RUNS,
            keep_strategy=KeepStrategy.NA,
        )

        entries = [
            RunEntry(
                id=RunEntryID(),
                board_id=board_id,
                identity_id=identity_id,
                score_event_id=ScoreEventID(),
                primary_value=float(100 + i * 10),
                player_name="Speedrunner",
            )
            for i in range(5)
        ]

        paginated = PaginatedResult(
            items=entries,
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_run_service = AsyncMock()
        mock_run_service.list_run_entries = AsyncMock(return_value=paginated)
        mock_run_service_cls.return_value = mock_run_service

        mock_session = AsyncMock()
        service = ScoreService(mock_session)

        pagination = PaginationParams(limit=10, cursor=None, sort=None)
        result = await service.list_scores(
            board_id=board_id,
            pagination=pagination,
        )

        assert len(result.items) == 5

    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.BoardStateService")
    async def test_list_scores_translates_value_sort_field_to_primary_value(
        self, mock_state_service_cls, mock_board_service_cls
    ):
        """Test that sort field 'value' is translated to 'primary_value' for the repository."""

        board_id = BoardID()
        board = Board(
            id=board_id,
            account_id=AccountID(),
            game_id=GameID(),
            name="High Scores",
            slug="high-scores",
            short_code="ABC123",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        paginated = PaginatedResult(
            items=[],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_state_service = AsyncMock()
        mock_state_service.list_board_states = AsyncMock(return_value=paginated)
        mock_state_service_cls.return_value = mock_state_service

        mock_session = AsyncMock()
        service = ScoreService(mock_session)

        pagination = PaginationParams(limit=10, cursor=None, sort="value:desc")
        await service.list_scores(board_id=board_id, pagination=pagination)

        # Verify the sort spec was translated before reaching the service
        call_kwargs = mock_state_service.list_board_states.call_args.kwargs
        passed_pagination = call_kwargs["pagination"]
        assert passed_pagination.sort_spec[0].name == "primary_value"
        assert passed_pagination.sort_spec[0].direction == PaginationSortDirection.DESC

    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.RunEntryService")
    async def test_list_scores_translates_value_sort_field_run_entry(
        self, mock_run_service_cls, mock_board_service_cls
    ):
        """Test that sort field 'value' is translated for RUN_RUNS boards too."""

        board_id = BoardID()
        board = Board(
            id=board_id,
            account_id=AccountID(),
            game_id=GameID(),
            name="Speedruns",
            slug="speedruns",
            short_code="SPD001",
            sort_direction=SortDirection.ASCENDING,
            board_type=BoardType.RUN_RUNS,
            keep_strategy=KeepStrategy.NA,
        )

        paginated = PaginatedResult(
            items=[],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_run_service = AsyncMock()
        mock_run_service.list_run_entries = AsyncMock(return_value=paginated)
        mock_run_service_cls.return_value = mock_run_service

        mock_session = AsyncMock()
        service = ScoreService(mock_session)

        pagination = PaginationParams(limit=10, cursor=None, sort="value:asc")
        await service.list_scores(board_id=board_id, pagination=pagination)

        call_kwargs = mock_run_service.list_run_entries.call_args.kwargs
        passed_pagination = call_kwargs["pagination"]
        assert passed_pagination.sort_spec[0].name == "primary_value"
        assert passed_pagination.sort_spec[0].direction == PaginationSortDirection.ASC

    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.BoardStateService")
    async def test_list_scores_with_around_score_id(
        self, mock_state_service_cls, mock_board_service_cls
    ):
        """Test listing scores centered around a specific score."""
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        target_state_id = BoardStateID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="High Scores",
            slug="high-scores",
            short_code="ABC123",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        target_state = BoardState(
            id=target_state_id,
            board_id=board_id,
            identity_id=IdentityID(),
            primary_value=500.0,
            player_name="Player4",
        )

        states = [
            BoardState(
                id=BoardStateID(),
                board_id=board_id,
                identity_id=IdentityID(),
                primary_value=float((i + 1) * 100),
                player_name=f"Player{i}",
            )
            for i in range(5)
        ]

        paginated = PaginatedResult(
            items=states,
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_state_service = AsyncMock()
        mock_state_service.get_board_state = AsyncMock(return_value=target_state)
        mock_state_service.list_board_states = AsyncMock(return_value=paginated)
        mock_state_service_cls.return_value = mock_state_service

        mock_session = AsyncMock()
        service = ScoreService(mock_session)

        pagination = PaginationParams(limit=5, cursor=None, sort=None)
        result = await service.list_scores(
            board_id=board_id,
            pagination=pagination,
            around_score_id=ScoreID(target_state_id.uuid),
        )

        assert len(result.items) == 5

    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.BoardStateService")
    async def test_list_scores_with_around_score_value(
        self, mock_state_service_cls, mock_board_service_cls
    ):
        """Test listing scores centered around a hypothetical value."""
        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="High Scores",
            slug="high-scores",
            short_code="ABC123",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        states = [
            BoardState(
                id=BoardStateID(),
                board_id=board_id,
                identity_id=IdentityID(),
                primary_value=float((i + 1) * 100),
                player_name=f"Player{i}",
            )
            for i in range(5)
        ]

        paginated = PaginatedResult(
            items=states,
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_state_service = AsyncMock()
        mock_state_service.list_board_states = AsyncMock(return_value=paginated)
        mock_state_service_cls.return_value = mock_state_service

        mock_session = AsyncMock()
        service = ScoreService(mock_session)

        pagination = PaginationParams(limit=5, cursor=None, sort=None)
        result = await service.list_scores(
            board_id=board_id,
            pagination=pagination,
            around_score_value=250.0,
        )

        assert len(result.items) > 0

    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.RunEntryService")
    async def test_list_scores_around_score_id_run_runs(
        self, mock_run_service_cls, mock_board_service_cls
    ):
        """Test list_scores with around_score_id on a RUN_RUNS board."""
        board_id = BoardID()
        target_entry_id = RunEntryID()
        identity_id = IdentityID()

        board = Board(
            id=board_id,
            account_id=AccountID(),
            game_id=GameID(),
            name="Speedruns",
            slug="speedruns",
            short_code="SPD001",
            sort_direction=SortDirection.ASCENDING,
            board_type=BoardType.RUN_RUNS,
            keep_strategy=KeepStrategy.NA,
        )

        target_entry = RunEntry(
            id=target_entry_id,
            board_id=board_id,
            identity_id=identity_id,
            score_event_id=ScoreEventID(),
            primary_value=500.0,
            player_name="Runner",
        )

        paginated = PaginatedResult(
            items=[target_entry],
            has_next=False,
            has_prev=False,
            next_position=None,
            prev_position=None,
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_run_service = AsyncMock()
        mock_run_service.get_run_entry = AsyncMock(return_value=target_entry)
        mock_run_service.list_run_entries = AsyncMock(return_value=paginated)
        mock_run_service_cls.return_value = mock_run_service

        service = ScoreService(AsyncMock())
        pagination = PaginationParams(limit=10, cursor=None, sort=None)
        around_id = ScoreID(target_entry_id.uuid)

        result = await service.list_scores(
            board_id=board_id,
            pagination=pagination,
            around_score_id=around_id,
        )

        assert len(result.items) == 1
        mock_run_service.get_run_entry.assert_called_once()

    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.RunEntryService")
    async def test_list_scores_around_score_id_run_runs_not_found(
        self, mock_run_service_cls, mock_board_service_cls
    ):
        """Test list_scores raises when around_score_id not found on RUN_RUNS board."""
        board_id = BoardID()

        board = Board(
            id=board_id,
            account_id=AccountID(),
            game_id=GameID(),
            name="Speedruns",
            slug="speedruns",
            short_code="SPD001",
            sort_direction=SortDirection.ASCENDING,
            board_type=BoardType.RUN_RUNS,
            keep_strategy=KeepStrategy.NA,
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_run_service = AsyncMock()
        mock_run_service.get_run_entry = AsyncMock(return_value=None)
        mock_run_service_cls.return_value = mock_run_service

        service = ScoreService(AsyncMock())
        pagination = PaginationParams(limit=10, cursor=None, sort=None)
        fake_id = ScoreID(RunEntryID().uuid)

        with pytest.raises(EntityNotFoundError):
            await service.list_scores(
                board_id=board_id,
                pagination=pagination,
                around_score_id=fake_id,
            )

    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.BoardStateService")
    async def test_list_scores_around_score_id_board_state_not_found(
        self, mock_state_service_cls, mock_board_service_cls
    ):
        """Test list_scores raises when around_score_id not found on RUN_IDENTITY board."""
        board_id = BoardID()

        board = Board(
            id=board_id,
            account_id=AccountID(),
            game_id=GameID(),
            name="High Scores",
            slug="high-scores",
            short_code="ABC123",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_state_service = AsyncMock()
        mock_state_service.get_board_state = AsyncMock(return_value=None)
        mock_state_service_cls.return_value = mock_state_service

        service = ScoreService(AsyncMock())
        pagination = PaginationParams(limit=10, cursor=None, sort=None)
        fake_id = ScoreID(BoardStateID().uuid)

        with pytest.raises(EntityNotFoundError):
            await service.list_scores(
                board_id=board_id,
                pagination=pagination,
                around_score_id=fake_id,
            )


@pytest.mark.asyncio
class TestScoreServiceRatioIntegration:
    """Tests for ratio board integration."""

    @patch("leadr.scores.services.score_service.BoardService")
    @patch("leadr.scores.services.score_service.ScoreEventService")
    @patch("leadr.scores.services.score_service.BoardStateService")
    @patch("leadr.scores.services.score_service.settings")
    async def test_submit_score_schedules_ratio_update(
        self,
        mock_settings,
        mock_board_state_service_cls,
        mock_event_service_cls,
        mock_board_service_cls,
    ):
        """Test that submitting to a source board schedules ratio updates."""
        mock_settings.ANTICHEAT_ENABLED = False

        account_id = AccountID()
        game_id = GameID()
        board_id = BoardID()
        identity_id = IdentityID()

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Kills",
            slug="kills",
            short_code="KLS001",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.COUNTER,
            keep_strategy=KeepStrategy.NA,
        )

        event = ScoreEvent(
            id=ScoreEventID(),
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"delta": 5.0},
        )

        state = BoardState(
            id=BoardStateID(),
            board_id=board_id,
            identity_id=identity_id,
            primary_value=5.0,
            player_name="Player1",
        )

        mock_board_service = AsyncMock()
        mock_board_service.get_by_id_or_raise = AsyncMock(return_value=board)
        mock_board_service_cls.return_value = mock_board_service

        mock_event_service = AsyncMock()
        mock_event_service.create_score_event = AsyncMock(return_value=event)
        mock_event_service_cls.return_value = mock_event_service

        mock_state_service = AsyncMock()
        mock_state_service.get_by_board_and_identity = AsyncMock(return_value=None)
        mock_state_service.create_board_state = AsyncMock(return_value=state)
        mock_state_service.find_dependent_ratio_boards = AsyncMock(return_value=[])
        mock_board_state_service_cls.return_value = mock_state_service

        mock_session = AsyncMock()
        service = ScoreService(mock_session)

        mock_background = Mock()

        await service.submit_score(
            board_id=board_id,
            identity_id=identity_id,
            delta=5.0,
            player_name="Player1",
            background_tasks=mock_background,
        )

        # Verify the code path works without errors
        # (No ratio boards configured, so no tasks added)

    @patch("leadr.scores.services.score_service.BoardStateService")
    async def test_schedule_ratio_updates_adds_background_tasks(self, mock_board_state_service_cls):
        """Test that dependent ratio configs get scheduled as background tasks."""
        board_id = BoardID()
        identity_id = IdentityID()
        ratio_board_id = BoardID()

        config1 = BoardRatioConfig(
            board_id=ratio_board_id,
            numerator_board_id=board_id,
            denominator_board_id=BoardID(),
        )
        config2 = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=board_id,
        )

        mock_state_service = AsyncMock()
        mock_state_service.find_dependent_ratio_boards = AsyncMock(return_value=[config1, config2])
        mock_board_state_service_cls.return_value = mock_state_service

        mock_background = Mock()
        service = ScoreService(AsyncMock())

        await service._schedule_ratio_updates(board_id, identity_id, mock_background)

        assert mock_background.add_task.call_count == 2

    @patch("leadr.scores.services.score_service.BoardStateService")
    async def test_recompute_ratio_background(self, mock_board_state_service_cls):
        """Test that _recompute_ratio_background calls recompute_ratio_for_identity."""
        identity_id = IdentityID()
        config = BoardRatioConfig(
            board_id=BoardID(),
            numerator_board_id=BoardID(),
            denominator_board_id=BoardID(),
        )

        mock_state_service = AsyncMock()
        mock_state_service.recompute_ratio_for_identity = AsyncMock()
        mock_board_state_service_cls.return_value = mock_state_service

        service = ScoreService(AsyncMock())
        await service._recompute_ratio_background(config, identity_id)

        mock_state_service.recompute_ratio_for_identity.assert_called_once_with(
            ratio_config=config,
            identity_id=identity_id,
        )


@pytest.mark.asyncio
class TestScoreServiceBuildPayload:
    """Tests for event payload construction."""

    async def test_build_event_payload_ratio_returns_empty(self, service):
        """Test that RATIO board type returns empty payload."""
        board = Board(
            id=BoardID(),
            account_id=AccountID(),
            game_id=GameID(),
            name="KD Ratio",
            slug="kd-ratio",
            short_code="KDR001",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RATIO,
            keep_strategy=KeepStrategy.NA,
        )

        result = service._build_event_payload(board, value=1.0, delta=None)
        assert result == {}


@pytest.mark.asyncio
class TestScoreServicePlayerNameAvailability:
    """Tests for public player name availability check."""

    @patch("leadr.scores.services.score_service.BoardStateRepository")
    @patch("leadr.scores.services.score_service.RunEntryRepository")
    async def test_check_player_name_available_across_boards(
        self, mock_run_repo_cls, mock_state_repo_cls, service
    ):
        """Test name available across multiple board types."""
        ri_board_id = BoardID()
        rr_board_id = BoardID()

        boards = [
            (ri_board_id, "High Scores", BoardType.RUN_IDENTITY),
            (rr_board_id, "Speedruns", BoardType.RUN_RUNS),
        ]

        mock_state_repo = AsyncMock()
        mock_state_repo.is_player_name_available = AsyncMock(return_value=True)
        mock_state_repo_cls.return_value = mock_state_repo

        mock_run_repo = AsyncMock()
        mock_run_repo.is_player_name_available = AsyncMock(return_value=True)
        mock_run_repo_cls.return_value = mock_run_repo

        normalised, is_available, conflicts = await service.check_player_name_availability(
            boards=boards,
            player_name="Player One",
        )

        assert normalised == "player one"
        assert is_available is True
        assert conflicts == []

    @patch("leadr.scores.services.score_service.BoardStateRepository")
    @patch("leadr.scores.services.score_service.RunEntryRepository")
    async def test_check_player_name_conflict_on_some_boards(
        self, mock_run_repo_cls, mock_state_repo_cls, service
    ):
        """Test name conflict detected on one of multiple boards."""
        ri_board_id = BoardID()
        rr_board_id = BoardID()

        boards = [
            (ri_board_id, "High Scores", BoardType.RUN_IDENTITY),
            (rr_board_id, "Speedruns", BoardType.RUN_RUNS),
        ]

        mock_state_repo = AsyncMock()
        mock_state_repo.is_player_name_available = AsyncMock(return_value=False)
        mock_state_repo_cls.return_value = mock_state_repo

        mock_run_repo = AsyncMock()
        mock_run_repo.is_player_name_available = AsyncMock(return_value=True)
        mock_run_repo_cls.return_value = mock_run_repo

        normalised, is_available, conflicts = await service.check_player_name_availability(
            boards=boards,
            player_name="TakenName",
        )

        assert normalised == "takenname"
        assert is_available is False
        assert len(conflicts) == 1
        assert conflicts[0] == (ri_board_id, "High Scores")

    async def test_check_player_name_empty_returns_available(self, service):
        """Test that whitespace-only name returns available with no conflicts."""
        normalised, is_available, conflicts = await service.check_player_name_availability(
            boards=[(BoardID(), "Board", BoardType.RUN_IDENTITY)],
            player_name="   ",
        )

        assert normalised == ""
        assert is_available is True
        assert conflicts == []
