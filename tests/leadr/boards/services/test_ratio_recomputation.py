"""Tests for RATIO board state recomputation."""

from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTasks

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository
from leadr.auth.domain.identity import Identity, IdentityKind
from leadr.auth.services.repositories import IdentityRepository
from leadr.boards.domain.board import Board, BoardType, KeepStrategy, SortDirection
from leadr.boards.domain.board_ratio_config import (
    BoardRatioConfig,
    RatioDisplay,
    TieBreaker,
    ZeroDenominatorPolicy,
)
from leadr.boards.domain.board_state import BoardState
from leadr.boards.services.board_state_service import BoardStateService
from leadr.boards.services.repositories import (
    BoardRatioConfigRepository,
    BoardRepository,
    BoardStateRepository,
)
from leadr.common.domain.ids import (
    AccountID,
    BoardID,
    BoardRatioConfigID,
    GameID,
    IdentityID,
)
from leadr.games.domain.game import Game
from leadr.games.services.repositories import GameRepository
from leadr.scores.services.score_service import ScoreService


@pytest_asyncio.fixture
async def ratio_test_fixtures(db_session: AsyncSession):
    """Create test fixtures with counter boards and a ratio board."""
    now = datetime.now(UTC)
    account_id = AccountID(uuid4())
    game_id = GameID(uuid4())

    # Create account
    account_repo = AccountRepository(db_session)
    account = Account(
        id=account_id,
        name="Test Account",
        slug=f"test-{uuid4().hex[:8]}",
        status=AccountStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    await account_repo.create(account)

    # Create game
    game_repo = GameRepository(db_session)
    game = Game(
        id=game_id,
        account_id=account_id,
        name="Test Game",
        slug=f"test-game-{uuid4().hex[:8]}",
        created_at=now,
        updated_at=now,
    )
    await game_repo.create(game)

    board_repo = BoardRepository(db_session)

    # Create numerator board (COUNTER - e.g., wins)
    numerator_board_id = BoardID(uuid4())
    numerator_board = Board(
        id=numerator_board_id,
        account_id=account_id,
        game_id=game_id,
        name="Wins",
        slug=f"wins-{uuid4().hex[:8]}",
        short_code=f"WIN{uuid4().hex[:4].upper()}",
        is_active=True,
        board_type=BoardType.COUNTER,
        sort_direction=SortDirection.DESCENDING,
        keep_strategy=KeepStrategy.NA,
        created_at=now,
        updated_at=now,
    )
    await board_repo.create(numerator_board)

    # Create denominator board (COUNTER - e.g., games played)
    denominator_board_id = BoardID(uuid4())
    denominator_board = Board(
        id=denominator_board_id,
        account_id=account_id,
        game_id=game_id,
        name="Games Played",
        slug=f"games-{uuid4().hex[:8]}",
        short_code=f"GAM{uuid4().hex[:4].upper()}",
        is_active=True,
        board_type=BoardType.COUNTER,
        sort_direction=SortDirection.DESCENDING,
        keep_strategy=KeepStrategy.NA,
        created_at=now,
        updated_at=now,
    )
    await board_repo.create(denominator_board)

    # Create ratio board (e.g., win rate)
    ratio_board_id = BoardID(uuid4())
    ratio_board = Board(
        id=ratio_board_id,
        account_id=account_id,
        game_id=game_id,
        name="Win Rate",
        slug=f"winrate-{uuid4().hex[:8]}",
        short_code=f"WR{uuid4().hex[:4].upper()}",
        is_active=True,
        board_type=BoardType.RATIO,
        sort_direction=SortDirection.DESCENDING,
        keep_strategy=KeepStrategy.NA,
        created_at=now,
        updated_at=now,
    )
    await board_repo.create(ratio_board)

    # Create ratio config
    ratio_config_repo = BoardRatioConfigRepository(db_session)
    ratio_config = BoardRatioConfig(
        id=BoardRatioConfigID(uuid4()),
        board_id=ratio_board_id,
        numerator_board_id=numerator_board_id,
        denominator_board_id=denominator_board_id,
        zero_denominator_policy=ZeroDenominatorPolicy.NULL,
        min_denominator=0,
        min_numerator=0,
        scale=1_000_000,
        display=RatioDisplay.PERCENT,
        decimals=2,
        tie_breaker=TieBreaker.NUMERATOR_DESC_DENOMINATOR_ASC,
        created_at=now,
        updated_at=now,
    )
    await ratio_config_repo.create(ratio_config)

    # Create identity
    identity_repo = IdentityRepository(db_session)
    identity_id = IdentityID(uuid4())
    identity = Identity(
        id=identity_id,
        account_id=account_id,
        game_id=game_id,
        kind=IdentityKind.DEVICE,
        external_key=f"dev_{uuid4().hex[:8]}",
        created_at=now,
        updated_at=now,
    )
    await identity_repo.create(identity)

    return {
        "account_id": account_id,
        "game_id": game_id,
        "numerator_board_id": numerator_board_id,
        "denominator_board_id": denominator_board_id,
        "ratio_board_id": ratio_board_id,
        "ratio_config": ratio_config,
        "identity_id": identity_id,
    }


@pytest.mark.asyncio
class TestRatioRecomputation:
    """Tests for BoardStateService ratio recomputation methods."""

    async def test_find_dependent_ratio_boards_for_numerator(
        self, db_session: AsyncSession, ratio_test_fixtures: dict
    ):
        """Test finding ratio boards that depend on a numerator board."""
        service = BoardStateService(db_session)

        configs = await service.find_dependent_ratio_boards(
            ratio_test_fixtures["numerator_board_id"]
        )

        assert len(configs) == 1
        assert configs[0].board_id == ratio_test_fixtures["ratio_board_id"]

    async def test_find_dependent_ratio_boards_for_denominator(
        self, db_session: AsyncSession, ratio_test_fixtures: dict
    ):
        """Test finding ratio boards that depend on a denominator board."""
        service = BoardStateService(db_session)

        configs = await service.find_dependent_ratio_boards(
            ratio_test_fixtures["denominator_board_id"]
        )

        assert len(configs) == 1
        assert configs[0].board_id == ratio_test_fixtures["ratio_board_id"]

    async def test_find_dependent_ratio_boards_returns_empty_for_unrelated(
        self, db_session: AsyncSession, ratio_test_fixtures: dict
    ):
        """Test that unrelated boards return no dependent ratio configs."""
        service = BoardStateService(db_session)

        # The ratio board itself should not return any dependent configs
        configs = await service.find_dependent_ratio_boards(ratio_test_fixtures["ratio_board_id"])

        assert len(configs) == 0

    async def test_recompute_ratio_calculates_correct_value(
        self, db_session: AsyncSession, ratio_test_fixtures: dict
    ):
        """Test that ratio is calculated correctly from numerator/denominator."""
        state_repo = BoardStateRepository(db_session)

        # Create numerator state (wins = 7)
        numerator_state = BoardState(
            board_id=ratio_test_fixtures["numerator_board_id"],
            identity_id=ratio_test_fixtures["identity_id"],
            primary_value=7.0,
            is_test=False,
        )
        await state_repo.create(numerator_state)

        # Create denominator state (games = 10)
        denominator_state = BoardState(
            board_id=ratio_test_fixtures["denominator_board_id"],
            identity_id=ratio_test_fixtures["identity_id"],
            primary_value=10.0,
            is_test=False,
        )
        await state_repo.create(denominator_state)

        # Recompute ratio
        service = BoardStateService(db_session)
        ratio_state = await service.recompute_ratio_for_identity(
            ratio_config=ratio_test_fixtures["ratio_config"],
            identity_id=ratio_test_fixtures["identity_id"],
        )

        assert ratio_state is not None
        # Expected: 7/10 * 1_000_000 = 700_000
        assert ratio_state.primary_value == 700_000.0
        assert ratio_state.board_id == ratio_test_fixtures["ratio_board_id"]

    async def test_recompute_ratio_respects_min_denominator(
        self, db_session: AsyncSession, ratio_test_fixtures: dict
    ):
        """Test that ratio is not rankable when denominator < min_denominator."""
        state_repo = BoardStateRepository(db_session)
        ratio_config_repo = BoardRatioConfigRepository(db_session)

        # Update ratio config to require min_denominator = 5
        config = ratio_test_fixtures["ratio_config"]
        config.min_denominator = 5
        await ratio_config_repo.update(config)

        # Create numerator state (wins = 3)
        numerator_state = BoardState(
            board_id=ratio_test_fixtures["numerator_board_id"],
            identity_id=ratio_test_fixtures["identity_id"],
            primary_value=3.0,
            is_test=False,
        )
        await state_repo.create(numerator_state)

        # Create denominator state (games = 3, which is < min_denominator)
        denominator_state = BoardState(
            board_id=ratio_test_fixtures["denominator_board_id"],
            identity_id=ratio_test_fixtures["identity_id"],
            primary_value=3.0,
            is_test=False,
        )
        await state_repo.create(denominator_state)

        # Recompute ratio
        service = BoardStateService(db_session)
        ratio_state = await service.recompute_ratio_for_identity(
            ratio_config=config,
            identity_id=ratio_test_fixtures["identity_id"],
        )

        # primary_value should be None (not rankable) because denominator < min_denominator
        assert ratio_state is not None
        assert ratio_state.primary_value is None

    async def test_recompute_ratio_handles_zero_denominator_null_policy(
        self, db_session: AsyncSession, ratio_test_fixtures: dict
    ):
        """Test that zero denominator with NULL policy returns None."""
        state_repo = BoardStateRepository(db_session)

        # Create numerator state (wins = 5)
        numerator_state = BoardState(
            board_id=ratio_test_fixtures["numerator_board_id"],
            identity_id=ratio_test_fixtures["identity_id"],
            primary_value=5.0,
            is_test=False,
        )
        await state_repo.create(numerator_state)

        # Create denominator state (games = 0)
        denominator_state = BoardState(
            board_id=ratio_test_fixtures["denominator_board_id"],
            identity_id=ratio_test_fixtures["identity_id"],
            primary_value=0.0,
            is_test=False,
        )
        await state_repo.create(denominator_state)

        # Recompute ratio (config has NULL policy by default)
        service = BoardStateService(db_session)
        ratio_state = await service.recompute_ratio_for_identity(
            ratio_config=ratio_test_fixtures["ratio_config"],
            identity_id=ratio_test_fixtures["identity_id"],
        )

        # Should be not rankable (primary_value = None)
        assert ratio_state is not None
        assert ratio_state.primary_value is None

    async def test_recompute_ratio_handles_zero_denominator_zero_policy(
        self, db_session: AsyncSession, ratio_test_fixtures: dict
    ):
        """Test that zero denominator with ZERO policy returns 0."""
        state_repo = BoardStateRepository(db_session)
        ratio_config_repo = BoardRatioConfigRepository(db_session)

        # Update config to use ZERO policy
        config = ratio_test_fixtures["ratio_config"]
        config.zero_denominator_policy = ZeroDenominatorPolicy.ZERO
        await ratio_config_repo.update(config)

        # Create numerator state
        numerator_state = BoardState(
            board_id=ratio_test_fixtures["numerator_board_id"],
            identity_id=ratio_test_fixtures["identity_id"],
            primary_value=5.0,
            is_test=False,
        )
        await state_repo.create(numerator_state)

        # Create denominator state (games = 0)
        denominator_state = BoardState(
            board_id=ratio_test_fixtures["denominator_board_id"],
            identity_id=ratio_test_fixtures["identity_id"],
            primary_value=0.0,
            is_test=False,
        )
        await state_repo.create(denominator_state)

        # Recompute ratio
        service = BoardStateService(db_session)
        ratio_state = await service.recompute_ratio_for_identity(
            ratio_config=config,
            identity_id=ratio_test_fixtures["identity_id"],
        )

        assert ratio_state is not None
        assert ratio_state.primary_value == 0.0

    async def test_recompute_ratio_stores_aux_data(
        self, db_session: AsyncSession, ratio_test_fixtures: dict
    ):
        """Test that ratio state stores numerator and denominator values in aux."""
        state_repo = BoardStateRepository(db_session)

        # Create states
        numerator_state = BoardState(
            board_id=ratio_test_fixtures["numerator_board_id"],
            identity_id=ratio_test_fixtures["identity_id"],
            primary_value=8.0,
            is_test=False,
        )
        await state_repo.create(numerator_state)

        denominator_state = BoardState(
            board_id=ratio_test_fixtures["denominator_board_id"],
            identity_id=ratio_test_fixtures["identity_id"],
            primary_value=10.0,
            is_test=False,
        )
        await state_repo.create(denominator_state)

        # Recompute ratio
        service = BoardStateService(db_session)
        ratio_state = await service.recompute_ratio_for_identity(
            ratio_config=ratio_test_fixtures["ratio_config"],
            identity_id=ratio_test_fixtures["identity_id"],
        )

        assert ratio_state is not None
        assert ratio_state.aux is not None
        assert ratio_state.aux["numerator_value"] == 8.0
        assert ratio_state.aux["denominator_value"] == 10.0

    async def test_recompute_ratio_returns_none_when_numerator_missing(
        self, db_session: AsyncSession, ratio_test_fixtures: dict
    ):
        """Test that recompute returns None when numerator state doesn't exist."""
        state_repo = BoardStateRepository(db_session)

        # Only create denominator state
        denominator_state = BoardState(
            board_id=ratio_test_fixtures["denominator_board_id"],
            identity_id=ratio_test_fixtures["identity_id"],
            primary_value=10.0,
            is_test=False,
        )
        await state_repo.create(denominator_state)

        # Recompute ratio (numerator missing)
        service = BoardStateService(db_session)
        ratio_state = await service.recompute_ratio_for_identity(
            ratio_config=ratio_test_fixtures["ratio_config"],
            identity_id=ratio_test_fixtures["identity_id"],
        )

        # Should return None (not create a state)
        assert ratio_state is None

    async def test_recompute_ratio_upserts_existing_state(
        self, db_session: AsyncSession, ratio_test_fixtures: dict
    ):
        """Test that recompute updates existing ratio state."""
        state_repo = BoardStateRepository(db_session)

        # Create initial states
        numerator_state = BoardState(
            board_id=ratio_test_fixtures["numerator_board_id"],
            identity_id=ratio_test_fixtures["identity_id"],
            primary_value=5.0,
            is_test=False,
        )
        await state_repo.create(numerator_state)

        denominator_state = BoardState(
            board_id=ratio_test_fixtures["denominator_board_id"],
            identity_id=ratio_test_fixtures["identity_id"],
            primary_value=10.0,
            is_test=False,
        )
        await state_repo.create(denominator_state)

        # First recompute
        service = BoardStateService(db_session)
        ratio_state_1 = await service.recompute_ratio_for_identity(
            ratio_config=ratio_test_fixtures["ratio_config"],
            identity_id=ratio_test_fixtures["identity_id"],
        )

        assert ratio_state_1 is not None
        assert ratio_state_1.primary_value == 500_000.0  # 5/10 * 1M

        # Update numerator
        numerator_state.primary_value = 8.0
        await state_repo.update(numerator_state)

        # Recompute again
        ratio_state_2 = await service.recompute_ratio_for_identity(
            ratio_config=ratio_test_fixtures["ratio_config"],
            identity_id=ratio_test_fixtures["identity_id"],
        )

        assert ratio_state_2 is not None
        assert ratio_state_2.primary_value == 800_000.0  # 8/10 * 1M
        # Should be the same entity (upsert, not create)
        assert ratio_state_2.id == ratio_state_1.id


@pytest.mark.asyncio
class TestScoreServiceRatioIntegration:
    """Tests for ScoreService integration with ratio updates."""

    async def test_score_submission_schedules_ratio_update(
        self, db_session: AsyncSession, ratio_test_fixtures: dict
    ):
        """Test that score submission schedules ratio board update."""
        # Create a mock BackgroundTasks to verify add_task is called
        mock_background_tasks = Mock(spec=BackgroundTasks)

        # Submit a score to the numerator board (wins)
        service = ScoreService(db_session)
        event, ranking_entry, anti_cheat_result = await service.submit_score(
            board_id=ratio_test_fixtures["numerator_board_id"],
            identity_id=ratio_test_fixtures["identity_id"],
            delta=1.0,  # COUNTER boards use delta
            background_tasks=mock_background_tasks,
        )

        assert event is not None
        assert ranking_entry is not None
        # Verify background task was scheduled
        mock_background_tasks.add_task.assert_called_once()

    async def test_score_submission_without_background_tasks_does_not_error(
        self, db_session: AsyncSession, ratio_test_fixtures: dict
    ):
        """Test that score submission works without background_tasks."""
        # Submit score without background_tasks (should not error)
        service = ScoreService(db_session)
        event, ranking_entry, anti_cheat_result = await service.submit_score(
            board_id=ratio_test_fixtures["numerator_board_id"],
            identity_id=ratio_test_fixtures["identity_id"],
            delta=1.0,
            background_tasks=None,  # Explicitly None
        )

        assert event is not None
        assert ranking_entry is not None
