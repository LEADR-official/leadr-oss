"""Tests for around query functionality in BoardStateRepository and RunEntryRepository."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository
from leadr.auth.domain.identity import Identity, IdentityKind
from leadr.auth.services.repositories import IdentityRepository
from leadr.boards.domain.board import Board, BoardType, KeepStrategy, SortDirection
from leadr.boards.domain.board_state import BoardState
from leadr.boards.domain.run_entry import RunEntry
from leadr.boards.services.repositories import (
    BoardRepository,
    BoardStateRepository,
    RunEntryRepository,
)
from leadr.common.domain.ids import (
    AccountID,
    BoardID,
    GameID,
    IdentityID,
    ScoreEventID,
)
from leadr.common.domain.pagination import SortDirection as PaginationSortDirection
from leadr.common.domain.pagination import SortField
from leadr.games.domain.game import Game
from leadr.games.services.repositories import GameRepository
from leadr.scores.domain.score_event import ScoreEvent
from leadr.scores.services.repositories import ScoreEventRepository


@pytest.mark.asyncio
class TestBoardStateRepositoryAroundQuery:
    """Tests for BoardStateRepository.execute_around_query method."""

    async def _create_test_fixtures(self, db_session: AsyncSession):
        """Create test fixtures with 7 board states."""
        now = datetime.now(UTC)
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())

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

        # Create board (DESCENDING - higher values are better)
        board_repo = BoardRepository(db_session)
        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            slug=f"test-board-{uuid4().hex[:8]}",
            short_code=f"TB{uuid4().hex[:4].upper()}",
            is_active=True,
            board_type=BoardType.RUN_IDENTITY,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

        # Create 7 identities and states with values 100-700
        identity_repo = IdentityRepository(db_session)
        state_repo = BoardStateRepository(db_session)
        states = []

        for value in [100, 200, 300, 400, 500, 600, 700]:
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

            state = BoardState(
                board_id=board_id,
                identity_id=identity_id,
                primary_value=float(value),
                is_test=False,
            )
            created_state = await state_repo.create(state)
            states.append(created_state)

        return {
            "board_id": board_id,
            "states": states,  # Sorted by value: [100, 200, 300, 400, 500, 600, 700]
            "sort_fields": [
                SortField(name="primary_value", direction=PaginationSortDirection.DESC),
                SortField(name="created_at", direction=PaginationSortDirection.DESC),
                SortField(name="id", direction=PaginationSortDirection.ASC),
            ],
        }

    async def test_around_query_returns_centered_window(self, db_session: AsyncSession):
        """Test around query centers results on target state."""
        fixtures = await self._create_test_fixtures(db_session)
        state_repo = BoardStateRepository(db_session)

        # Target is state with value 400 (index 3)
        target_state = fixtures["states"][3]
        assert target_state.primary_value == 400.0

        result = await state_repo.execute_around_query(
            board_id=fixtures["board_id"],
            target_state=target_state,
            sort_fields=fixtures["sort_fields"],
            limit=5,
        )

        # With DESC sort and limit=5:
        # Expected order: [600, 500, 400, 300, 200] - 2 above, target, 2 below
        assert len(result.items) == 5
        values = [s.primary_value for s in result.items]
        assert values == [600.0, 500.0, 400.0, 300.0, 200.0]

        # Should have more items on both sides
        assert result.has_prev is True  # 700 above
        assert result.has_next is True  # 100 below

    async def test_around_query_at_top_fills_below(self, db_session: AsyncSession):
        """Test around query fills from below when target is at top."""
        fixtures = await self._create_test_fixtures(db_session)
        state_repo = BoardStateRepository(db_session)

        # Target is state with value 700 (highest, index 6)
        target_state = fixtures["states"][6]
        assert target_state.primary_value == 700.0

        result = await state_repo.execute_around_query(
            board_id=fixtures["board_id"],
            target_state=target_state,
            sort_fields=fixtures["sort_fields"],
            limit=5,
        )

        # With DESC sort, target at top, limit=5:
        # Expected: [700, 600, 500, 400, 300] - 0 above (none exist), target, 4 below
        assert len(result.items) == 5
        values = [s.primary_value for s in result.items]
        assert values == [700.0, 600.0, 500.0, 400.0, 300.0]

        # No items above, more below
        assert result.has_prev is False
        assert result.has_next is True  # 200, 100 below

    async def test_around_query_at_bottom_fills_above(self, db_session: AsyncSession):
        """Test around query fills from above when target is at bottom."""
        fixtures = await self._create_test_fixtures(db_session)
        state_repo = BoardStateRepository(db_session)

        # Target is state with value 100 (lowest, index 0)
        target_state = fixtures["states"][0]
        assert target_state.primary_value == 100.0

        result = await state_repo.execute_around_query(
            board_id=fixtures["board_id"],
            target_state=target_state,
            sort_fields=fixtures["sort_fields"],
            limit=5,
        )

        # With DESC sort, target at bottom, limit=5:
        # Expected: [500, 400, 300, 200, 100] - 4 above, target, 0 below
        assert len(result.items) == 5
        values = [s.primary_value for s in result.items]
        assert values == [500.0, 400.0, 300.0, 200.0, 100.0]

        # More items above, none below
        assert result.has_prev is True  # 700, 600 above
        assert result.has_next is False


@pytest.mark.asyncio
class TestRunEntryRepositoryAroundQuery:
    """Tests for RunEntryRepository.execute_around_query method."""

    async def _create_test_fixtures(self, db_session: AsyncSession):
        """Create test fixtures with 7 run entries."""
        now = datetime.now(UTC)
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

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

        # Create board (RUN_RUNS type, DESCENDING)
        board_repo = BoardRepository(db_session)
        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            slug=f"test-board-{uuid4().hex[:8]}",
            short_code=f"RUN{uuid4().hex[:4].upper()}",
            is_active=True,
            board_type=BoardType.RUN_RUNS,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.NA,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

        # Create identity
        identity_repo = IdentityRepository(db_session)
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

        # Create 7 entries with values 100-700
        event_repo = ScoreEventRepository(db_session)
        entry_repo = RunEntryRepository(db_session)
        entries = []

        for value in [100, 200, 300, 400, 500, 600, 700]:
            # Create score event
            score_event_id = ScoreEventID(uuid4())
            event = ScoreEvent(
                id=score_event_id,
                account_id=account_id,
                game_id=game_id,
                board_id=board_id,
                identity_id=identity_id,
                event_payload={"value": value},
                is_test=False,
                created_at=now,
            )
            await event_repo.create(event)

            # Create run entry
            entry = RunEntry(
                board_id=board_id,
                identity_id=identity_id,
                score_event_id=score_event_id,
                primary_value=float(value),
                is_test=False,
            )
            created_entry = await entry_repo.create(entry)
            entries.append(created_entry)

        return {
            "board_id": board_id,
            "entries": entries,  # Sorted by value: [100, 200, 300, 400, 500, 600, 700]
            "sort_fields": [
                SortField(name="primary_value", direction=PaginationSortDirection.DESC),
                SortField(name="created_at", direction=PaginationSortDirection.DESC),
                SortField(name="id", direction=PaginationSortDirection.ASC),
            ],
        }

    async def test_around_query_returns_centered_window(self, db_session: AsyncSession):
        """Test around query centers results on target entry."""
        fixtures = await self._create_test_fixtures(db_session)
        entry_repo = RunEntryRepository(db_session)

        # Target is entry with value 400 (index 3)
        target_entry = fixtures["entries"][3]
        assert target_entry.primary_value == 400.0

        result = await entry_repo.execute_around_query(
            board_id=fixtures["board_id"],
            target_entry=target_entry,
            sort_fields=fixtures["sort_fields"],
            limit=5,
        )

        # With DESC sort and limit=5:
        # Expected order: [600, 500, 400, 300, 200] - 2 above, target, 2 below
        assert len(result.items) == 5
        values = [e.primary_value for e in result.items]
        assert values == [600.0, 500.0, 400.0, 300.0, 200.0]

        # Should have more items on both sides
        assert result.has_prev is True  # 700 above
        assert result.has_next is True  # 100 below


@pytest.mark.asyncio
class TestBoardStateRepositoryAroundValueQuery:
    """Tests for BoardStateRepository.execute_around_value_query method."""

    async def _create_test_fixtures(self, db_session: AsyncSession):
        """Create test fixtures with 7 board states."""
        now = datetime.now(UTC)
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())

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

        # Create board (DESCENDING - higher values are better)
        board_repo = BoardRepository(db_session)
        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            slug=f"test-board-{uuid4().hex[:8]}",
            short_code=f"TB{uuid4().hex[:4].upper()}",
            is_active=True,
            board_type=BoardType.RUN_IDENTITY,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

        # Create 7 identities and states with values 100-700
        identity_repo = IdentityRepository(db_session)
        state_repo = BoardStateRepository(db_session)
        states = []

        for value in [100, 200, 300, 400, 500, 600, 700]:
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

            state = BoardState(
                board_id=board_id,
                identity_id=identity_id,
                primary_value=float(value),
                is_test=False,
            )
            created_state = await state_repo.create(state)
            states.append(created_state)

        return {
            "board_id": board_id,
            "account_id": account_id,
            "game_id": game_id,
            "states": states,
            "sort_fields": [
                SortField(name="primary_value", direction=PaginationSortDirection.DESC),
                SortField(name="created_at", direction=PaginationSortDirection.DESC),
                SortField(name="id", direction=PaginationSortDirection.ASC),
            ],
        }

    async def test_around_value_query_returns_placeholder(self, db_session: AsyncSession):
        """Test around value query includes a placeholder entry."""
        fixtures = await self._create_test_fixtures(db_session)
        state_repo = BoardStateRepository(db_session)

        # Query around value 450 (between 400 and 500)
        result = await state_repo.execute_around_value_query(
            board_id=fixtures["board_id"],
            target_value=450.0,
            sort_fields=fixtures["sort_fields"],
            limit=5,
        )

        # Should include a placeholder at position 3 (after 500, before 400)
        assert len(result.items) == 5
        values = [s.primary_value for s in result.items]
        # DESC sort: [600, 500, 450 (placeholder), 400, 300]
        assert values == [600.0, 500.0, 450.0, 400.0, 300.0]

        # The placeholder should be marked as is_placeholder=True
        placeholder = result.items[2]
        assert placeholder.is_placeholder is True
        assert placeholder.primary_value == 450.0

    async def test_around_value_query_placeholder_has_correct_rank(self, db_session: AsyncSession):
        """Test placeholder has the correct hypothetical rank."""
        fixtures = await self._create_test_fixtures(db_session)
        state_repo = BoardStateRepository(db_session)

        # Query around value 450 (between 400 and 500)
        result = await state_repo.execute_around_value_query(
            board_id=fixtures["board_id"],
            target_value=450.0,
            sort_fields=fixtures["sort_fields"],
            limit=5,
        )

        # Placeholder rank should be 4 (3 values better: 700, 600, 500 + 1 for rank)
        placeholder = result.items[2]
        assert placeholder.rank == 4

    async def test_around_value_query_at_top(self, db_session: AsyncSession):
        """Test around value query with value higher than all entries."""
        fixtures = await self._create_test_fixtures(db_session)
        state_repo = BoardStateRepository(db_session)

        # Query around value 800 (higher than all - would be rank 1)
        result = await state_repo.execute_around_value_query(
            board_id=fixtures["board_id"],
            target_value=800.0,
            sort_fields=fixtures["sort_fields"],
            limit=5,
        )

        # Placeholder should be first
        assert len(result.items) == 5
        values = [s.primary_value for s in result.items]
        # DESC sort: [800 (placeholder), 700, 600, 500, 400]
        assert values == [800.0, 700.0, 600.0, 500.0, 400.0]

        placeholder = result.items[0]
        assert placeholder.is_placeholder is True
        assert placeholder.rank == 1
        assert result.has_prev is False
        assert result.has_next is True

    async def test_around_value_query_at_bottom(self, db_session: AsyncSession):
        """Test around value query with value lower than all entries."""
        fixtures = await self._create_test_fixtures(db_session)
        state_repo = BoardStateRepository(db_session)

        # Query around value 50 (lower than all - would be rank 8)
        result = await state_repo.execute_around_value_query(
            board_id=fixtures["board_id"],
            target_value=50.0,
            sort_fields=fixtures["sort_fields"],
            limit=5,
        )

        # Placeholder should be last
        assert len(result.items) == 5
        values = [s.primary_value for s in result.items]
        # DESC sort: [400, 300, 200, 100, 50 (placeholder)]
        assert values == [400.0, 300.0, 200.0, 100.0, 50.0]

        placeholder = result.items[4]
        assert placeholder.is_placeholder is True
        assert placeholder.rank == 8  # After all 7 existing entries
        assert result.has_prev is True
        assert result.has_next is False

    async def test_around_value_query_same_as_existing(self, db_session: AsyncSession):
        """Test around value query with value matching an existing entry."""
        fixtures = await self._create_test_fixtures(db_session)
        state_repo = BoardStateRepository(db_session)

        # Query around value 400 (same as existing entry)
        # Placeholder should appear at top of same-value group (newest timestamp)
        result = await state_repo.execute_around_value_query(
            board_id=fixtures["board_id"],
            target_value=400.0,
            sort_fields=fixtures["sort_fields"],
            limit=5,
        )

        # Should include both placeholder and existing 400 entry
        assert len(result.items) == 5
        values = [s.primary_value for s in result.items]
        # DESC sort with placeholder at top of 400-value group:
        # [600, 500, 400 (placeholder), 400 (real), 300]
        assert values == [600.0, 500.0, 400.0, 400.0, 300.0]

        # First 400 is placeholder, second is real
        assert result.items[2].is_placeholder is True
        assert result.items[3].is_placeholder is False


@pytest.mark.asyncio
class TestRunEntryRepositoryAroundValueQuery:
    """Tests for RunEntryRepository.execute_around_value_query method."""

    async def _create_test_fixtures(self, db_session: AsyncSession):
        """Create test fixtures with 7 run entries."""
        now = datetime.now(UTC)
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

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

        # Create board (RUN_RUNS type, DESCENDING)
        board_repo = BoardRepository(db_session)
        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            slug=f"test-board-{uuid4().hex[:8]}",
            short_code=f"RUN{uuid4().hex[:4].upper()}",
            is_active=True,
            board_type=BoardType.RUN_RUNS,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.NA,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

        # Create identity
        identity_repo = IdentityRepository(db_session)
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

        # Create 7 entries with values 100-700
        event_repo = ScoreEventRepository(db_session)
        entry_repo = RunEntryRepository(db_session)
        entries = []

        for value in [100, 200, 300, 400, 500, 600, 700]:
            # Create score event
            score_event_id = ScoreEventID(uuid4())
            event = ScoreEvent(
                id=score_event_id,
                account_id=account_id,
                game_id=game_id,
                board_id=board_id,
                identity_id=identity_id,
                event_payload={"value": value},
                is_test=False,
                created_at=now,
            )
            await event_repo.create(event)

            # Create run entry
            entry = RunEntry(
                board_id=board_id,
                identity_id=identity_id,
                score_event_id=score_event_id,
                primary_value=float(value),
                is_test=False,
            )
            created_entry = await entry_repo.create(entry)
            entries.append(created_entry)

        return {
            "board_id": board_id,
            "account_id": account_id,
            "game_id": game_id,
            "identity_id": identity_id,
            "entries": entries,
            "sort_fields": [
                SortField(name="primary_value", direction=PaginationSortDirection.DESC),
                SortField(name="created_at", direction=PaginationSortDirection.DESC),
                SortField(name="id", direction=PaginationSortDirection.ASC),
            ],
        }

    async def test_around_value_query_returns_placeholder(self, db_session: AsyncSession):
        """Test around value query includes a placeholder entry."""
        fixtures = await self._create_test_fixtures(db_session)
        entry_repo = RunEntryRepository(db_session)

        # Query around value 450 (between 400 and 500)
        result = await entry_repo.execute_around_value_query(
            board_id=fixtures["board_id"],
            target_value=450.0,
            sort_fields=fixtures["sort_fields"],
            limit=5,
        )

        # Should include a placeholder at position 3 (after 500, before 400)
        assert len(result.items) == 5
        values = [e.primary_value for e in result.items]
        # DESC sort: [600, 500, 450 (placeholder), 400, 300]
        assert values == [600.0, 500.0, 450.0, 400.0, 300.0]

        # The placeholder should be marked as is_placeholder=True
        placeholder = result.items[2]
        assert placeholder.is_placeholder is True
        assert placeholder.primary_value == 450.0

    async def test_around_value_query_placeholder_has_correct_rank(self, db_session: AsyncSession):
        """Test placeholder has the correct hypothetical rank."""
        fixtures = await self._create_test_fixtures(db_session)
        entry_repo = RunEntryRepository(db_session)

        # Query around value 450 (between 400 and 500)
        result = await entry_repo.execute_around_value_query(
            board_id=fixtures["board_id"],
            target_value=450.0,
            sort_fields=fixtures["sort_fields"],
            limit=5,
        )

        # Placeholder rank should be 4 (3 values better: 700, 600, 500 + 1 for rank)
        placeholder = result.items[2]
        assert placeholder.rank == 4


@pytest.mark.asyncio
class TestBoardStateAroundQueryRanks:
    """Tests for rank computation in BoardStateRepository.execute_around_query."""

    async def _create_test_fixtures(self, db_session: AsyncSession):
        """Create test fixtures with 10 board states for rank testing."""
        now = datetime.now(UTC)
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())

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

        # Create board (DESCENDING - higher values are better)
        board_repo = BoardRepository(db_session)
        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            slug=f"test-board-{uuid4().hex[:8]}",
            short_code=f"TB{uuid4().hex[:4].upper()}",
            is_active=True,
            board_type=BoardType.RUN_IDENTITY,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

        # Create 10 identities and states with values 100-1000
        identity_repo = IdentityRepository(db_session)
        state_repo = BoardStateRepository(db_session)
        states = []

        for value in [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]:
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

            state = BoardState(
                board_id=board_id,
                identity_id=identity_id,
                primary_value=float(value),
                is_test=False,
            )
            created_state = await state_repo.create(state)
            states.append(created_state)

        return {
            "board_id": board_id,
            "states": states,  # [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
            "sort_fields": [
                SortField(name="primary_value", direction=PaginationSortDirection.DESC),
                SortField(name="created_at", direction=PaginationSortDirection.DESC),
                SortField(name="id", direction=PaginationSortDirection.ASC),
            ],
        }

    async def test_around_query_returns_correct_absolute_ranks(self, db_session: AsyncSession):
        """Verify execute_around_query sets correct absolute ranks on returned items.

        When querying around a score at rank 6 (value 500 in DESC order),
        returned ranks should be [4, 5, 6, 7, 8] not [1, 2, 3, 4, 5].
        """
        fixtures = await self._create_test_fixtures(db_session)
        state_repo = BoardStateRepository(db_session)

        # Target is state with value 500 (rank 6 in desc order: 1000=1, 900=2, ... 500=6)
        target_state = fixtures["states"][4]  # Value 500
        assert target_state.primary_value == 500.0

        result = await state_repo.execute_around_query(
            board_id=fixtures["board_id"],
            target_state=target_state,
            sort_fields=fixtures["sort_fields"],
            limit=5,
        )

        # With DESC sort and limit=5, centered on rank 6:
        # Values: [700, 600, 500, 400, 300]
        # Absolute ranks: [4, 5, 6, 7, 8]
        assert len(result.items) == 5
        values = [s.primary_value for s in result.items]
        assert values == [700.0, 600.0, 500.0, 400.0, 300.0]

        ranks = [s.rank for s in result.items]
        assert ranks == [4, 5, 6, 7, 8], f"Expected absolute ranks [4, 5, 6, 7, 8], got {ranks}"

    async def test_around_query_at_top_returns_correct_ranks(self, db_session: AsyncSession):
        """When target is rank 1, returned ranks start at 1."""
        fixtures = await self._create_test_fixtures(db_session)
        state_repo = BoardStateRepository(db_session)

        # Target is state with value 1000 (rank 1)
        target_state = fixtures["states"][9]  # Value 1000
        assert target_state.primary_value == 1000.0

        result = await state_repo.execute_around_query(
            board_id=fixtures["board_id"],
            target_state=target_state,
            sort_fields=fixtures["sort_fields"],
            limit=5,
        )

        # With target at rank 1 and limit=5:
        # Values: [1000, 900, 800, 700, 600]
        # Absolute ranks: [1, 2, 3, 4, 5]
        assert len(result.items) == 5
        values = [s.primary_value for s in result.items]
        assert values == [1000.0, 900.0, 800.0, 700.0, 600.0]

        ranks = [s.rank for s in result.items]
        assert ranks == [1, 2, 3, 4, 5], f"Expected ranks [1, 2, 3, 4, 5], got {ranks}"

    async def test_around_query_at_bottom_returns_correct_ranks(self, db_session: AsyncSession):
        """When target is at bottom, ranks reflect true position."""
        fixtures = await self._create_test_fixtures(db_session)
        state_repo = BoardStateRepository(db_session)

        # Target is state with value 100 (rank 10)
        target_state = fixtures["states"][0]  # Value 100
        assert target_state.primary_value == 100.0

        result = await state_repo.execute_around_query(
            board_id=fixtures["board_id"],
            target_state=target_state,
            sort_fields=fixtures["sort_fields"],
            limit=5,
        )

        # With target at rank 10 and limit=5, window fills from above:
        # Values: [500, 400, 300, 200, 100]
        # Absolute ranks: [6, 7, 8, 9, 10]
        assert len(result.items) == 5
        values = [s.primary_value for s in result.items]
        assert values == [500.0, 400.0, 300.0, 200.0, 100.0]

        ranks = [s.rank for s in result.items]
        assert ranks == [6, 7, 8, 9, 10], f"Expected ranks [6, 7, 8, 9, 10], got {ranks}"


@pytest.mark.asyncio
class TestRunEntryAroundQueryRanks:
    """Tests for rank computation in RunEntryRepository.execute_around_query."""

    async def _create_test_fixtures(self, db_session: AsyncSession):
        """Create test fixtures with 10 run entries for rank testing."""
        now = datetime.now(UTC)
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())

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

        # Create board (RUN_RUNS type, DESCENDING)
        board_repo = BoardRepository(db_session)
        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            slug=f"test-board-{uuid4().hex[:8]}",
            short_code=f"RUN{uuid4().hex[:4].upper()}",
            is_active=True,
            board_type=BoardType.RUN_RUNS,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.NA,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

        # Create identity
        identity_repo = IdentityRepository(db_session)
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

        # Create 10 entries with values 100-1000
        event_repo = ScoreEventRepository(db_session)
        entry_repo = RunEntryRepository(db_session)
        entries = []

        for value in [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]:
            # Create score event
            score_event_id = ScoreEventID(uuid4())
            event = ScoreEvent(
                id=score_event_id,
                account_id=account_id,
                game_id=game_id,
                board_id=board_id,
                identity_id=identity_id,
                event_payload={"value": value},
                is_test=False,
                created_at=now,
            )
            await event_repo.create(event)

            # Create run entry
            entry = RunEntry(
                board_id=board_id,
                identity_id=identity_id,
                score_event_id=score_event_id,
                primary_value=float(value),
                is_test=False,
            )
            created_entry = await entry_repo.create(entry)
            entries.append(created_entry)

        return {
            "board_id": board_id,
            "entries": entries,  # [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
            "sort_fields": [
                SortField(name="primary_value", direction=PaginationSortDirection.DESC),
                SortField(name="created_at", direction=PaginationSortDirection.DESC),
                SortField(name="id", direction=PaginationSortDirection.ASC),
            ],
        }

    async def test_around_query_returns_correct_absolute_ranks(self, db_session: AsyncSession):
        """Verify execute_around_query sets correct absolute ranks on returned items."""
        fixtures = await self._create_test_fixtures(db_session)
        entry_repo = RunEntryRepository(db_session)

        # Target is entry with value 500 (rank 6 in desc order)
        target_entry = fixtures["entries"][4]  # Value 500
        assert target_entry.primary_value == 500.0

        result = await entry_repo.execute_around_query(
            board_id=fixtures["board_id"],
            target_entry=target_entry,
            sort_fields=fixtures["sort_fields"],
            limit=5,
        )

        # Values: [700, 600, 500, 400, 300]
        # Absolute ranks: [4, 5, 6, 7, 8]
        assert len(result.items) == 5
        values = [e.primary_value for e in result.items]
        assert values == [700.0, 600.0, 500.0, 400.0, 300.0]

        ranks = [e.rank for e in result.items]
        assert ranks == [4, 5, 6, 7, 8], f"Expected absolute ranks [4, 5, 6, 7, 8], got {ranks}"

    async def test_around_query_at_top_returns_correct_ranks(self, db_session: AsyncSession):
        """When target is rank 1, returned ranks start at 1."""
        fixtures = await self._create_test_fixtures(db_session)
        entry_repo = RunEntryRepository(db_session)

        # Target is entry with value 1000 (rank 1)
        target_entry = fixtures["entries"][9]  # Value 1000
        assert target_entry.primary_value == 1000.0

        result = await entry_repo.execute_around_query(
            board_id=fixtures["board_id"],
            target_entry=target_entry,
            sort_fields=fixtures["sort_fields"],
            limit=5,
        )

        # Values: [1000, 900, 800, 700, 600]
        # Absolute ranks: [1, 2, 3, 4, 5]
        assert len(result.items) == 5
        values = [e.primary_value for e in result.items]
        assert values == [1000.0, 900.0, 800.0, 700.0, 600.0]

        ranks = [e.rank for e in result.items]
        assert ranks == [1, 2, 3, 4, 5], f"Expected ranks [1, 2, 3, 4, 5], got {ranks}"

    async def test_around_query_at_bottom_returns_correct_ranks(self, db_session: AsyncSession):
        """When target is at bottom, ranks reflect true position."""
        fixtures = await self._create_test_fixtures(db_session)
        entry_repo = RunEntryRepository(db_session)

        # Target is entry with value 100 (rank 10)
        target_entry = fixtures["entries"][0]  # Value 100
        assert target_entry.primary_value == 100.0

        result = await entry_repo.execute_around_query(
            board_id=fixtures["board_id"],
            target_entry=target_entry,
            sort_fields=fixtures["sort_fields"],
            limit=5,
        )

        # Values: [500, 400, 300, 200, 100]
        # Absolute ranks: [6, 7, 8, 9, 10]
        assert len(result.items) == 5
        values = [e.primary_value for e in result.items]
        assert values == [500.0, 400.0, 300.0, 200.0, 100.0]

        ranks = [e.rank for e in result.items]
        assert ranks == [6, 7, 8, 9, 10], f"Expected ranks [6, 7, 8, 9, 10], got {ranks}"


@pytest.mark.asyncio
class TestAroundValueQueryAllItemRanks:
    """Tests for rank computation on ALL items in around_value queries."""

    async def _create_test_fixtures(self, db_session: AsyncSession):
        """Create test fixtures with 7 board states."""
        now = datetime.now(UTC)
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())

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

        # Create board (DESCENDING - higher values are better)
        board_repo = BoardRepository(db_session)
        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            slug=f"test-board-{uuid4().hex[:8]}",
            short_code=f"TB{uuid4().hex[:4].upper()}",
            is_active=True,
            board_type=BoardType.RUN_IDENTITY,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

        # Create 7 identities and states with values 100-700
        identity_repo = IdentityRepository(db_session)
        state_repo = BoardStateRepository(db_session)
        states = []

        for value in [100, 200, 300, 400, 500, 600, 700]:
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

            state = BoardState(
                board_id=board_id,
                identity_id=identity_id,
                primary_value=float(value),
                is_test=False,
            )
            created_state = await state_repo.create(state)
            states.append(created_state)

        return {
            "board_id": board_id,
            "states": states,
            "sort_fields": [
                SortField(name="primary_value", direction=PaginationSortDirection.DESC),
                SortField(name="created_at", direction=PaginationSortDirection.DESC),
                SortField(name="id", direction=PaginationSortDirection.ASC),
            ],
        }

    async def test_around_value_query_returns_correct_ranks_for_all_items(
        self, db_session: AsyncSession
    ):
        """Verify all items (not just placeholder) have correct absolute ranks.

        With scores 700=1, 600=2, 500=3, 400=4, 300=5, 200=6, 100=7
        and querying around value 450 (hypothetical rank 4):
        - score 600 should have rank 2
        - score 500 should have rank 3
        - placeholder (450) should have rank 4
        - score 400 should have rank 5
        - score 300 should have rank 6
        """
        fixtures = await self._create_test_fixtures(db_session)
        state_repo = BoardStateRepository(db_session)

        result = await state_repo.execute_around_value_query(
            board_id=fixtures["board_id"],
            target_value=450.0,
            sort_fields=fixtures["sort_fields"],
            limit=5,
        )

        # Values: [600, 500, 450 (placeholder), 400, 300]
        assert len(result.items) == 5
        values = [s.primary_value for s in result.items]
        assert values == [600.0, 500.0, 450.0, 400.0, 300.0]

        # Ranks should be absolute: [2, 3, 4, 5, 6]
        ranks = [s.rank for s in result.items]
        assert ranks == [2, 3, 4, 5, 6], f"Expected ranks [2, 3, 4, 5, 6], got {ranks}"

        # Verify placeholder is marked
        assert result.items[2].is_placeholder is True
