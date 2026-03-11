"""Tests for the new score submission flow with board type handlers."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.services.account_service import AccountService
from leadr.auth.domain.identity import IdentityKind
from leadr.auth.services.device_service import DeviceService
from leadr.auth.services.identity_service import IdentityService
from leadr.boards.domain.board import BoardType, KeepStrategy, SortDirection
from leadr.boards.domain.board_state import BoardState
from leadr.boards.domain.run_entry import RunEntry
from leadr.boards.services.board_service import BoardService
from leadr.boards.services.run_entry_service import RunEntryService
from leadr.games.services.game_service import GameService
from leadr.scores.domain.score_event import ScoreEvent
from leadr.scores.services.score_service import ScoreService


@pytest.mark.asyncio
class TestSubmitScoreValidation:
    """Tests for submit_score validation."""

    async def test_submit_score_requires_value_for_run_identity_board(
        self, db_session: AsyncSession
    ):
        """RUN_IDENTITY boards require value in payload."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account-run-id",
        )

        # Create game
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="High Scores",
            slug="high-scores-val-1",
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create identity
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="test-device-123",
        )

        service = ScoreService(db_session)

        with pytest.raises(ValueError, match="value is required"):
            await service.submit_score(
                board_id=board.id,
                identity_id=identity.id,
                # Missing value
            )

    async def test_submit_score_requires_value_for_run_runs_board(self, db_session: AsyncSession):
        """RUN_RUNS boards require value in payload."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account-run-runs",
        )

        # Create game
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="All Runs",
            slug="all-runs-val-1",
            board_type=BoardType.RUN_RUNS,
            keep_strategy=KeepStrategy.NA,
        )

        # Create identity
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="test-device-456",
        )

        service = ScoreService(db_session)

        with pytest.raises(ValueError, match="value is required"):
            await service.submit_score(
                board_id=board.id,
                identity_id=identity.id,
                # Missing value
            )

    async def test_submit_score_requires_delta_for_counter_board(self, db_session: AsyncSession):
        """COUNTER boards require delta in payload."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account-counter",
        )

        # Create game
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Total Kills",
            slug="total-kills-val-1",
            board_type=BoardType.COUNTER,
            keep_strategy=KeepStrategy.NA,
        )

        # Create identity
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="test-device-789",
        )

        service = ScoreService(db_session)

        with pytest.raises(ValueError, match="delta is required"):
            await service.submit_score(
                board_id=board.id,
                identity_id=identity.id,
                # Missing delta
            )

    async def test_submit_score_rejects_direct_submission_to_ratio_board(
        self, db_session: AsyncSession
    ):
        """RATIO boards do not accept direct submissions."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account-ratio",
        )

        # Create game
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Win Rate",
            slug="win-rate-val-1",
            board_type=BoardType.RATIO,
            keep_strategy=KeepStrategy.NA,
        )

        # Create identity
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="test-device-ratio",
        )

        service = ScoreService(db_session)

        with pytest.raises(ValueError, match="RATIO boards do not accept direct submissions"):
            await service.submit_score(
                board_id=board.id,
                identity_id=identity.id,
                value=100.0,
            )


@pytest.mark.asyncio
class TestRunIdentitySubmission:
    """Tests for RUN_IDENTITY board submissions."""

    async def test_submit_score_creates_event_and_board_state(
        self,
        db_session: AsyncSession,
    ):
        """First submission creates both event and board state."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account-ri-1",
        )

        # Create game
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="High Scores",
            slug="high-scores-ri-1",
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create identity
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="test-device-ri-1",
        )

        # Submit score
        service = ScoreService(db_session)
        event, ranking_entry, anti_cheat_result = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=1000.0,
            player_name="TestPlayer",
        )

        # Verify event was created
        assert isinstance(event, ScoreEvent)
        assert event.board_id == board.id
        assert event.identity_id == identity.id
        assert event.event_payload == {"value": 1000.0}

        # Verify board state was created
        assert isinstance(ranking_entry, BoardState)
        assert ranking_entry.board_id == board.id
        assert ranking_entry.identity_id == identity.id
        assert ranking_entry.primary_value == 1000.0

    async def test_submit_score_best_strategy_keeps_better_score(
        self,
        db_session: AsyncSession,
    ):
        """BEST strategy keeps higher score for DESCENDING board."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account-ri-best",
        )

        # Create game
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Best Scores",
            slug="best-scores-ri-1",
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
            sort_direction=SortDirection.DESCENDING,
        )

        # Create identity
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="test-device-ri-best",
        )

        service = ScoreService(db_session)

        # Submit first score
        _, state1, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=500.0,
        )
        assert isinstance(state1, BoardState)
        assert state1.primary_value == 500.0

        # Submit better score
        _, state2, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=1000.0,
        )
        assert isinstance(state2, BoardState)
        assert state2.primary_value == 1000.0  # Updated

        # Submit worse score
        _, state3, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=300.0,
        )
        assert isinstance(state3, BoardState)
        assert state3.primary_value == 1000.0  # Still the best

    async def test_submit_score_first_strategy_keeps_first_score(
        self,
        db_session: AsyncSession,
    ):
        """FIRST strategy keeps initial score."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account-ri-first",
        )

        # Create game
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="First Scores",
            slug="first-scores-ri-1",
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.FIRST,
        )

        # Create identity
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="test-device-ri-first",
        )

        service = ScoreService(db_session)

        # Submit first score
        _, state1, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=500.0,
        )
        assert isinstance(state1, BoardState)
        assert state1.primary_value == 500.0

        # Submit another score - should be ignored
        _, state2, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=1000.0,
        )
        assert isinstance(state2, BoardState)
        assert state2.primary_value == 500.0  # Still first

    async def test_submit_score_latest_strategy_always_updates(
        self,
        db_session: AsyncSession,
    ):
        """LATEST strategy always updates to latest score."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account-ri-latest",
        )

        # Create game
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Latest Scores",
            slug="latest-scores-ri-1",
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.LATEST,
        )

        # Create identity
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="test-device-ri-latest",
        )

        service = ScoreService(db_session)

        # Submit first score
        _, state1, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=1000.0,
        )
        assert isinstance(state1, BoardState)
        assert state1.primary_value == 1000.0

        # Submit worse score - should still update
        _, state2, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=300.0,
        )
        assert isinstance(state2, BoardState)
        assert state2.primary_value == 300.0  # Updated to latest


@pytest.mark.asyncio
class TestRunRunsSubmission:
    """Tests for RUN_RUNS board submissions."""

    async def test_submit_score_creates_run_entry(
        self,
        db_session: AsyncSession,
    ):
        """Each submission creates a new run entry."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account-rr-1",
        )

        # Create game
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="All Runs",
            slug="all-runs-rr-1",
            board_type=BoardType.RUN_RUNS,
            keep_strategy=KeepStrategy.NA,
        )

        # Create identity
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="test-device-rr-1",
        )

        service = ScoreService(db_session)

        # Submit first score
        event1, entry1, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=1000.0,
        )
        assert isinstance(entry1, RunEntry)
        assert entry1.primary_value == 1000.0
        assert entry1.score_event_id == event1.id

        # Submit second score
        event2, entry2, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=2000.0,
        )
        assert isinstance(entry2, RunEntry)
        assert entry2.primary_value == 2000.0
        assert entry2.id != entry1.id  # Different entry

        # Verify both entries exist
        run_entry_service = RunEntryService(db_session)
        result = await run_entry_service.list_run_entries(
            board_id=board.id,
            identity_id=identity.id,
        )
        assert len(result.items) == 2


@pytest.mark.asyncio
class TestCounterSubmission:
    """Tests for COUNTER board submissions."""

    async def test_submit_score_accumulates_delta(
        self,
        db_session: AsyncSession,
    ):
        """COUNTER boards accumulate delta values."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account-ctr-1",
        )

        # Create game
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Total Kills",
            slug="total-kills-ctr-1",
            board_type=BoardType.COUNTER,
            keep_strategy=KeepStrategy.NA,
        )

        # Create identity
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="test-device-ctr-1",
        )

        service = ScoreService(db_session)

        # Submit first delta
        event1, state1, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            delta=10.0,
        )
        assert isinstance(state1, BoardState)
        assert state1.primary_value == 10.0
        assert event1.event_payload == {"delta": 10.0}

        # Submit second delta
        event2, state2, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            delta=5.0,
        )
        assert isinstance(state2, BoardState)
        assert state2.primary_value == 15.0  # Accumulated

        # Submit negative delta
        event3, state3, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            delta=-3.0,
        )
        assert isinstance(state3, BoardState)
        assert state3.primary_value == 12.0  # 15 - 3


@pytest.mark.asyncio
class TestGeoDataHandling:
    """Tests for geo data in score events."""

    async def test_submit_score_includes_geo_data(
        self,
        db_session: AsyncSession,
    ):
        """Score events include geo data when provided."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account-geo-1",
        )

        # Create game
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Geo Test",
            slug="geo-test-1",
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create identity
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="test-device-geo-1",
        )

        service = ScoreService(db_session)

        event, _, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=1000.0,
            timezone="America/New_York",
            country="US",
            city="New York",
        )

        assert event.timezone == "America/New_York"
        assert event.country == "US"
        assert event.city == "New York"


@pytest.mark.asyncio
class TestAuxDataInBoardState:
    """Tests for auxiliary data in board states."""

    async def test_run_identity_aux_contains_selected_event(
        self,
        db_session: AsyncSession,
    ):
        """RUN_IDENTITY board state aux contains selected_event_id."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account-aux-1",
        )

        # Create game
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Aux Test",
            slug="aux-test-1",
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create identity
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="test-device-aux-1",
        )

        service = ScoreService(db_session)

        event, state, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=1000.0,
        )

        assert isinstance(state, BoardState)
        assert state.aux is not None
        assert "selected_event_id" in state.aux
        assert state.aux["selected_event_id"] == str(event.id)
        assert "event_count" in state.aux
        assert state.aux["event_count"] == 1

    async def test_counter_aux_contains_event_count(
        self,
        db_session: AsyncSession,
    ):
        """COUNTER board state aux contains event_count and last_event_id."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account-ctr-aux-1",
        )

        # Create game
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Counter Aux Test",
            slug="counter-aux-test-1",
            board_type=BoardType.COUNTER,
            keep_strategy=KeepStrategy.NA,
        )

        # Create identity
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="test-device-ctr-aux-1",
        )

        service = ScoreService(db_session)

        # First submission
        event1, state1, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            delta=10.0,
        )
        assert isinstance(state1, BoardState)
        assert state1.aux is not None
        assert state1.aux["event_count"] == 1
        assert state1.aux["last_event_id"] == str(event1.id)

        # Second submission
        event2, state2, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            delta=5.0,
        )
        assert isinstance(state2, BoardState)
        assert state2.aux is not None
        assert state2.aux["event_count"] == 2
        assert state2.aux["last_event_id"] == str(event2.id)


@pytest.mark.asyncio
class TestValueDisplayAndMetadataPersistence:
    """Tests for value_display and metadata persistence in score submissions."""

    async def test_run_identity_persists_value_display_and_metadata(
        self,
        db_session: AsyncSession,
    ):
        """RUN_IDENTITY board persists value_display and metadata."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account-vd-ri",
        )

        # Create game
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Value Display Test",
            slug="value-display-ri",
            board_type=BoardType.RUN_IDENTITY,
            keep_strategy=KeepStrategy.BEST,
        )

        # Create identity
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="test-device-vd-ri",
        )

        service = ScoreService(db_session)

        # Submit score with value_display and metadata
        _, state, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=1234.0,
            value_display="1,234",
            metadata={"level": 5, "weapon": "sword"},
        )

        assert isinstance(state, BoardState)
        assert state.value_display == "1,234"
        assert state.metadata == {"level": 5, "weapon": "sword"}

    async def test_run_runs_persists_value_display_and_metadata(
        self,
        db_session: AsyncSession,
    ):
        """RUN_RUNS board persists value_display and metadata on run entry."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account-vd-rr",
        )

        # Create game
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Value Display Runs",
            slug="value-display-rr",
            board_type=BoardType.RUN_RUNS,
            keep_strategy=KeepStrategy.NA,
        )

        # Create identity
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="test-device-vd-rr",
        )

        service = ScoreService(db_session)

        # Submit score with value_display and metadata
        _, entry, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            value=5678.0,
            value_display="5,678",
            metadata={"difficulty": "hard"},
        )

        assert isinstance(entry, RunEntry)
        assert entry.value_display == "5,678"
        assert entry.metadata == {"difficulty": "hard"}

    async def test_counter_persists_value_display_and_metadata(
        self,
        db_session: AsyncSession,
    ):
        """COUNTER board persists value_display and metadata."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Test Account",
            slug="test-account-vd-ctr",
        )

        # Create game
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board
        board_service = BoardService(db_session)
        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Value Display Counter",
            slug="value-display-ctr",
            board_type=BoardType.COUNTER,
            keep_strategy=KeepStrategy.NA,
        )

        # Create identity
        identity_service = IdentityService(db_session, device_service=DeviceService(db_session))
        identity, _ = await identity_service.get_or_create_identity(
            account_id=account.id,
            game_id=game.id,
            kind=IdentityKind.DEVICE,
            external_key="test-device-vd-ctr",
        )

        service = ScoreService(db_session)

        # Submit score with value_display and metadata
        _, state, _ = await service.submit_score(
            board_id=board.id,
            identity_id=identity.id,
            delta=100.0,
            value_display="100",
            metadata={"source": "daily_bonus"},
        )

        assert isinstance(state, BoardState)
        assert state.value_display == "100"
        assert state.metadata == {"source": "daily_bonus"}
