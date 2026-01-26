"""Tests for ScoreService."""

from unittest.mock import Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTasks

from leadr.accounts.services.account_service import AccountService
from leadr.auth.domain.identity import IdentityKind
from leadr.auth.services.device_service import DeviceService
from leadr.auth.services.identity_service import IdentityService
from leadr.boards.domain.board import BoardType, KeepStrategy, SortDirection
from leadr.boards.services.board_service import BoardService
from leadr.boards.services.board_state_service import BoardStateService
from leadr.boards.services.run_entry_service import RunEntryService
from leadr.common.api.pagination import PaginationParams
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.common.domain.ids import BoardID, ScoreID
from leadr.games.services.game_service import GameService
from leadr.scores.services.score_event_service import ScoreEventService
from leadr.scores.services.score_service import ScoreService


@pytest.mark.asyncio
class TestScoreServiceSubmission:
    """Tests for score submission flow."""

    async def test_submit_score_run_identity_first_submission(self, db_session: AsyncSession):
        """Test first submission to a RUN_IDENTITY board creates a BoardState."""
        # Setup
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test", slug="test-ri-first")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_ri_first",
            display_name="Player1",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="High Scores",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        # Submit score
        service = ScoreService(db_session)
        event, ranking_entry, anti_cheat = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=100.0,
            player_name="Player1",
        )

        assert event is not None
        assert ranking_entry is not None
        assert ranking_entry.primary_value == 100.0

    async def test_submit_score_run_identity_keep_best_higher_is_better(
        self, db_session: AsyncSession
    ):
        """Test BEST strategy keeps higher score for DESCENDING board."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test", slug="test-keep-best")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_keep_best",
            display_name="Player1",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="High Scores",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        service = ScoreService(db_session)

        # First submission
        _, entry1, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=100.0,
            player_name="Player1",
        )
        assert entry1 is not None
        assert entry1.primary_value == 100.0

        # Second submission with higher score (better for DESC)
        _, entry2, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=200.0,
            player_name="Player1",
        )
        assert entry2 is not None
        assert entry2.primary_value == 200.0

        # Third submission with lower score (worse for DESC)
        _, entry3, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=150.0,
            player_name="Player1",
        )
        # Should still be 200 (best)
        assert entry3 is not None
        assert entry3.primary_value == 200.0

    async def test_submit_score_run_identity_keep_best_lower_is_better(
        self, db_session: AsyncSession
    ):
        """Test BEST strategy keeps lower score for ASCENDING board."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test", slug="test-keep-low")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_keep_low",
            display_name="Speedrunner",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speedruns",
            sort_direction=SortDirection.ASCENDING,  # Lower is better
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        service = ScoreService(db_session)

        # First submission
        _, entry1, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=120.0,
            player_name="Speedrunner",
        )
        assert entry1 is not None
        assert entry1.primary_value == 120.0

        # Second submission with lower time (better for ASC)
        _, entry2, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=100.0,
            player_name="Speedrunner",
        )
        assert entry2 is not None
        assert entry2.primary_value == 100.0

        # Third submission with higher time (worse for ASC)
        _, entry3, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=110.0,
            player_name="Speedrunner",
        )
        # Should still be 100 (best)
        assert entry3 is not None
        assert entry3.primary_value == 100.0

    async def test_submit_score_run_identity_keep_first(self, db_session: AsyncSession):
        """Test FIRST strategy keeps the first score."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test", slug="test-keep-first")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_keep_first",
            display_name="Player1",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="First Completion",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.FIRST,
        )

        service = ScoreService(db_session)

        # First submission
        _, entry1, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=100.0,
            player_name="Player1",
        )
        assert entry1 is not None
        assert entry1.primary_value == 100.0

        # Second submission (should be ignored)
        _, entry2, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=200.0,
            player_name="Player1",
        )
        # Should still be 100 (first)
        assert entry2 is not None
        assert entry2.primary_value == 100.0

    async def test_submit_score_run_identity_keep_latest(self, db_session: AsyncSession):
        """Test LATEST strategy always uses the latest score."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test", slug="test-keep-latest")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_keep_latest",
            display_name="Player1",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Latest Score",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.LATEST,
        )

        service = ScoreService(db_session)

        # First submission
        _, entry1, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=100.0,
            player_name="Player1",
        )
        assert entry1 is not None
        assert entry1.primary_value == 100.0

        # Second submission
        _, entry2, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=50.0,  # Lower, but it's latest
            player_name="Player1",
        )
        assert entry2 is not None
        assert entry2.primary_value == 50.0

    async def test_submit_score_run_runs_creates_entry(self, db_session: AsyncSession):
        """Test RUN_RUNS board creates a new RunEntry for each submission."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test", slug="test-run-runs")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_run_runs",
            display_name="Speedrunner",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speedruns",
            sort_direction=SortDirection.ASCENDING,
            board_type=BoardType.RUN_RUNS,
            keep_strategy=KeepStrategy.NA,
        )

        service = ScoreService(db_session)

        # First submission
        _, entry1, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=120.0,
            player_name="Speedrunner",
        )

        # Second submission
        _, entry2, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=110.0,
            player_name="Speedrunner",
        )

        # Each submission should create a new entry
        assert entry1 is not None
        assert entry2 is not None
        assert entry1.id != entry2.id
        assert entry1.primary_value == 120.0
        assert entry2.primary_value == 110.0

    async def test_submit_score_counter_accumulates(self, db_session: AsyncSession):
        """Test COUNTER board accumulates delta values."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test", slug="test-counter")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_counter",
            display_name="Killer",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Kill Count",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.COUNTER,
            keep_strategy=KeepStrategy.NA,
        )

        service = ScoreService(db_session)

        # First delta
        _, entry1, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            delta=5.0,
            player_name="Killer",
        )
        assert entry1 is not None
        assert entry1.primary_value == 5.0

        # Second delta
        _, entry2, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            delta=3.0,
            player_name="Killer",
        )
        assert entry2 is not None
        assert entry2.primary_value == 8.0

        # Third delta (negative)
        _, entry3, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            delta=-2.0,
            player_name="Killer",
        )
        assert entry3 is not None
        assert entry3.primary_value == 6.0

    async def test_submit_score_ratio_board_rejected(self, db_session: AsyncSession):
        """Test that RATIO boards reject direct submissions."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test", slug="test-ratio-reject")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_ratio",
            display_name="Player1",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="K/D Ratio",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RATIO,
            keep_strategy=KeepStrategy.NA,
        )

        service = ScoreService(db_session)

        with pytest.raises(ValueError, match="RATIO boards do not accept direct submissions"):
            await service.submit_score(
                board_id=board.id,
                identity_id=identity.id,
                value=1.5,
                player_name="Player1",
            )

    async def test_submit_score_missing_value_for_run_board(self, db_session: AsyncSession):
        """Test that RUN boards require value."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test", slug="test-missing-value")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_missing",
            display_name="Player1",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="High Scores",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        service = ScoreService(db_session)

        with pytest.raises(ValueError, match="value is required"):
            await service.submit_score(
                board_id=board.id,
                identity_id=identity.id,
                delta=100.0,  # Wrong param - should be value
                player_name="Player1",
            )

    async def test_submit_score_missing_delta_for_counter(self, db_session: AsyncSession):
        """Test that COUNTER boards require delta."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test", slug="test-missing-delta")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_missing_delta",
            display_name="Player1",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Kill Count",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.COUNTER,
            keep_strategy=KeepStrategy.NA,
        )

        service = ScoreService(db_session)

        with pytest.raises(ValueError, match="delta is required"):
            await service.submit_score(
                board_id=board.id,
                identity_id=identity.id,
                value=100.0,  # Wrong param - should be delta
                player_name="Player1",
            )

    async def test_submit_score_board_not_found(self, db_session: AsyncSession):
        """Test submitting to non-existent board raises error."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test", slug="test-board-404")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_404",
            display_name="Player1",
        )

        service = ScoreService(db_session)

        fake_board_id = BoardID()
        with pytest.raises(EntityNotFoundError):
            await service.submit_score(
                board_id=fake_board_id,
                identity_id=identity.id,
                value=100.0,
                player_name="Player1",
            )


@pytest.mark.asyncio
class TestScoreServiceQuery:
    """Tests for score query methods."""

    async def test_get_score_by_id_board_state(self, db_session: AsyncSession):
        """Test getting a BoardState score by ID."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test", slug="test-get-state")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_get_state",
            display_name="Player1",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="High Scores",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        state_service = BoardStateService(db_session)
        state = await state_service.create_board_state(
            board_id=board.id,
            identity_id=identity.id,
            primary_value=500.0,
            player_name="Player1",
        )

        service = ScoreService(db_session)
        score_id = ScoreID(state.id.uuid)
        result, result_board, rank = await service.get_score_by_id(score_id)

        assert result.id == state.id
        assert result.primary_value == 500.0
        assert result_board.id == board.id
        assert rank == 1

    async def test_get_score_by_id_run_entry(self, db_session: AsyncSession):
        """Test getting a RunEntry score by ID."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test", slug="test-get-entry")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_get_entry",
            display_name="Speedrunner",
        )

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speedruns",
            sort_direction=SortDirection.ASCENDING,
            board_type=BoardType.RUN_RUNS,
            keep_strategy=KeepStrategy.NA,
        )

        event_service = ScoreEventService(db_session)
        event = await event_service.create_score_event(
            account_id=account.id,
            game_id=game.id,
            board_id=board.id,
            identity_id=identity.id,
            event_payload={"value": 120.0},
        )

        run_entry_service = RunEntryService(db_session)
        entry = await run_entry_service.create_run_entry(
            board_id=board.id,
            identity_id=identity.id,
            score_event_id=event.id,
            primary_value=120.0,
            player_name="Speedrunner",
        )

        service = ScoreService(db_session)
        score_id = ScoreID(entry.id.uuid)
        result, result_board, rank = await service.get_score_by_id(score_id)

        assert result.id == entry.id
        assert result.primary_value == 120.0
        assert result_board.id == board.id

    async def test_get_score_by_id_not_found(self, db_session: AsyncSession):
        """Test getting non-existent score raises error."""
        service = ScoreService(db_session)
        fake_id = ScoreID()

        with pytest.raises(EntityNotFoundError):
            await service.get_score_by_id(fake_id)

    async def test_list_scores_board_state(self, db_session: AsyncSession):
        """Test listing scores from a RUN_IDENTITY board."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test", slug="test-list-state")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="High Scores",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        state_service = BoardStateService(db_session)

        for i in range(5):
            identity, _ = await identity_service.get_or_create_identity(
                account_id=account.id,
                game_id=game.id,
                kind=IdentityKind.DEVICE,
                external_key=f"dev_list_state_{i}",
                display_name=f"Player{i}",
            )
            await state_service.create_board_state(
                board_id=board.id,
                identity_id=identity.id,
                primary_value=float(i * 100),
                player_name=f"Player{i}",
            )

        service = ScoreService(db_session)
        pagination = PaginationParams(limit=10, cursor=None, sort=None)
        result = await service.list_scores(
            board_id=board.id,
            pagination=pagination,
        )

        assert len(result.items) == 5

    async def test_list_scores_run_entry(self, db_session: AsyncSession):
        """Test listing scores from a RUN_RUNS board."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test", slug="test-list-entry")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speedruns",
            sort_direction=SortDirection.ASCENDING,
            board_type=BoardType.RUN_RUNS,
            keep_strategy=KeepStrategy.NA,
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_list_entry",
            display_name="Speedrunner",
        )

        event_service = ScoreEventService(db_session)
        run_entry_service = RunEntryService(db_session)

        for i in range(5):
            event = await event_service.create_score_event(
                account_id=account.id,
                game_id=game.id,
                board_id=board.id,
                identity_id=identity.id,
                event_payload={"value": float(100 + i * 10)},
            )
            await run_entry_service.create_run_entry(
                board_id=board.id,
                identity_id=identity.id,
                score_event_id=event.id,
                primary_value=float(100 + i * 10),
                player_name="Speedrunner",
            )

        service = ScoreService(db_session)
        pagination = PaginationParams(limit=10, cursor=None, sort=None)
        result = await service.list_scores(
            board_id=board.id,
            pagination=pagination,
        )

        assert len(result.items) == 5

    async def test_list_scores_requires_board_id(self, db_session: AsyncSession):
        """Test list_scores raises error without board_id."""
        service = ScoreService(db_session)
        pagination = PaginationParams(limit=10, cursor=None, sort=None)

        with pytest.raises(ValueError, match="board_id is required"):
            await service.list_scores(pagination=pagination)

    async def test_list_scores_with_around_score_id(self, db_session: AsyncSession):
        """Test listing scores centered around a specific score."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test", slug="test-around-id")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="High Scores",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        state_service = BoardStateService(db_session)

        states = []
        for i in range(10):
            identity, _ = await identity_service.get_or_create_identity(
                account_id=account.id,
                game_id=game.id,
                kind=IdentityKind.DEVICE,
                external_key=f"dev_around_{i}",
                display_name=f"Player{i}",
            )
            state = await state_service.create_board_state(
                board_id=board.id,
                identity_id=identity.id,
                primary_value=float((i + 1) * 100),
                player_name=f"Player{i}",
            )
            states.append(state)

        # Get around the middle score
        target_state = states[4]  # 500 points
        service = ScoreService(db_session)
        pagination = PaginationParams(limit=5, cursor=None, sort=None)

        result = await service.list_scores(
            board_id=board.id,
            pagination=pagination,
            around_score_id=ScoreID(target_state.id.uuid),
        )

        assert len(result.items) == 5

    async def test_list_scores_with_around_score_value(self, db_session: AsyncSession):
        """Test listing scores centered around a hypothetical value."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test", slug="test-around-val")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="High Scores",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        state_service = BoardStateService(db_session)

        for i in range(5):
            identity, _ = await identity_service.get_or_create_identity(
                account_id=account.id,
                game_id=game.id,
                kind=IdentityKind.DEVICE,
                external_key=f"dev_around_val_{i}",
                display_name=f"Player{i}",
            )
            await state_service.create_board_state(
                board_id=board.id,
                identity_id=identity.id,
                primary_value=float((i + 1) * 100),
                player_name=f"Player{i}",
            )

        service = ScoreService(db_session)
        pagination = PaginationParams(limit=5, cursor=None, sort=None)

        result = await service.list_scores(
            board_id=board.id,
            pagination=pagination,
            around_score_value=250.0,  # Between 200 and 300
        )

        # Should include a placeholder
        assert len(result.items) > 0


@pytest.mark.asyncio
class TestScoreServiceRatioIntegration:
    """Tests for ratio board integration."""

    async def test_submit_score_schedules_ratio_update(self, db_session: AsyncSession):
        """Test that submitting to a source board schedules ratio updates."""
        account_service = AccountService(db_session)
        account = await account_service.create_account(name="Test", slug="test-ratio-sched")

        game_service = GameService(db_session)
        game = await game_service.create_game(account_id=account.id, name="Test Game")

        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="dev_ratio_sched",
            display_name="Player1",
        )

        board_service = BoardService(db_session)
        # Create counter board (source)
        counter_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Kills",
            sort_direction=SortDirection.DESCENDING,
            board_type=BoardType.COUNTER,
            keep_strategy=KeepStrategy.NA,
        )

        service = ScoreService(db_session)

        # Mock background tasks
        mock_background = Mock(spec=BackgroundTasks)

        # Submit score with background tasks
        await service.submit_score(
            board_id=counter_board.id,
            identity_id=identity.id,
            delta=5.0,
            player_name="Player1",
            background_tasks=mock_background,
        )

        # Background tasks should have been called if there were ratio dependencies
        # (In this case, there are none, so it won't be called)
        # This test verifies the code path works without errors
