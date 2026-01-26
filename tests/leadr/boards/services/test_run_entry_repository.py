"""Tests for RunEntryRepository."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository
from leadr.auth.domain.identity import Identity, IdentityKind
from leadr.auth.services.repositories import IdentityRepository
from leadr.boards.adapters.orm import RunEntryORM
from leadr.boards.domain.board import Board, BoardType, KeepStrategy, SortDirection
from leadr.boards.domain.run_entry import RunEntry
from leadr.boards.services.repositories import BoardRepository, RunEntryRepository
from leadr.common.domain.ids import (
    AccountID,
    BoardID,
    GameID,
    IdentityID,
    RunEntryID,
    ScoreEventID,
)
from leadr.games.domain.game import Game
from leadr.games.services.repositories import GameRepository
from leadr.scores.domain.score_event import ScoreEvent
from leadr.scores.services.repositories import ScoreEventRepository


class TestRunEntryRepository:
    """Test suite for RunEntryRepository unit tests."""

    def test_to_domain_conversion(self, db_session):
        """Test _to_domain method converts ORM to domain entity."""
        repository = RunEntryRepository(db_session)
        board_id = uuid4()
        identity_id = uuid4()
        score_event_id = uuid4()
        now = datetime.now(UTC)

        orm = RunEntryORM(
            id=uuid4(),
            board_id=board_id,
            identity_id=identity_id,
            score_event_id=score_event_id,
            primary_value=100.0,
            player_name="Test Player",
            is_test=False,
            created_at=now,
            updated_at=now,
        )

        domain = repository._to_domain(orm)

        assert isinstance(domain, RunEntry)
        assert domain.board_id.uuid == board_id
        assert domain.identity_id.uuid == identity_id
        assert domain.score_event_id.uuid == score_event_id
        assert domain.primary_value == 100.0

    def test_to_orm_conversion(self, db_session):
        """Test _to_orm method converts domain to ORM entity."""
        repository = RunEntryRepository(db_session)
        domain = RunEntry(
            board_id=BoardID(uuid4()),
            identity_id=IdentityID(uuid4()),
            score_event_id=ScoreEventID(uuid4()),
            primary_value=200.0,
        )

        orm = repository._to_orm(domain)

        assert isinstance(orm, RunEntryORM)
        assert orm.id == domain.id.uuid
        assert orm.board_id == domain.board_id.uuid
        assert orm.identity_id == domain.identity_id.uuid
        assert orm.score_event_id == domain.score_event_id.uuid
        assert orm.primary_value == 200.0

    def test_get_orm_class(self, db_session):
        """Test _get_orm_class returns RunEntryORM."""
        repository = RunEntryRepository(db_session)
        assert repository._get_orm_class() == RunEntryORM


@pytest.mark.asyncio
class TestRunEntryRepositoryCRUD:
    """Integration tests for RunEntryRepository CRUD operations."""

    async def _create_test_fixtures(self, db_session: AsyncSession):
        """Create common test fixtures."""
        now = datetime.now(UTC)
        account_id = AccountID(uuid4())
        game_id = GameID(uuid4())
        board_id = BoardID(uuid4())
        identity_id = IdentityID(uuid4())
        score_event_id = ScoreEventID(uuid4())

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

        # Create board (RUN_RUNS type)
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

        # Create score event
        event_repo = ScoreEventRepository(db_session)
        event = ScoreEvent(
            id=score_event_id,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 1000},
            is_test=False,
            created_at=now,
        )
        await event_repo.create(event)

        return {
            "account_id": account_id,
            "game_id": game_id,
            "board_id": board_id,
            "identity_id": identity_id,
            "score_event_id": score_event_id,
            "now": now,
        }

    async def test_create_run_entry(self, db_session: AsyncSession):
        """Test creating a run entry."""
        fixtures = await self._create_test_fixtures(db_session)

        entry_repo = RunEntryRepository(db_session)
        entry = RunEntry(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_id"],
            score_event_id=fixtures["score_event_id"],
            primary_value=1000.0,
        )

        created = await entry_repo.create(entry)

        assert created.id == entry.id
        assert created.board_id == fixtures["board_id"]
        assert created.identity_id == fixtures["identity_id"]
        assert created.score_event_id == fixtures["score_event_id"]
        assert created.primary_value == 1000.0

    async def test_get_by_id(self, db_session: AsyncSession):
        """Test getting a run entry by ID."""
        fixtures = await self._create_test_fixtures(db_session)

        entry_repo = RunEntryRepository(db_session)
        entry = RunEntry(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_id"],
            score_event_id=fixtures["score_event_id"],
            primary_value=500.0,
        )
        await entry_repo.create(entry)

        retrieved = await entry_repo.get_by_id(entry.id)

        assert retrieved is not None
        assert retrieved.id == entry.id
        assert retrieved.primary_value == 500.0

    async def test_get_by_id_not_found(self, db_session: AsyncSession):
        """Test getting a non-existent run entry returns None."""
        entry_repo = RunEntryRepository(db_session)
        result = await entry_repo.get_by_id(RunEntryID(uuid4()))
        assert result is None

    async def test_get_by_board_and_score_event(self, db_session: AsyncSession):
        """Test getting a run entry by board and score event."""
        fixtures = await self._create_test_fixtures(db_session)

        entry_repo = RunEntryRepository(db_session)
        entry = RunEntry(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_id"],
            score_event_id=fixtures["score_event_id"],
            primary_value=750.0,
        )
        await entry_repo.create(entry)

        retrieved = await entry_repo.get_by_board_and_score_event(
            fixtures["board_id"],
            fixtures["score_event_id"],
        )

        assert retrieved is not None
        assert retrieved.id == entry.id
        assert retrieved.primary_value == 750.0

    async def test_get_by_board_and_score_event_not_found(self, db_session: AsyncSession):
        """Test getting a non-existent run entry by board and score event returns None."""
        entry_repo = RunEntryRepository(db_session)
        result = await entry_repo.get_by_board_and_score_event(
            BoardID(uuid4()),
            ScoreEventID(uuid4()),
        )
        assert result is None


@pytest.mark.asyncio
class TestRunEntryRepositoryIsTestFilter:
    """Tests for RunEntryRepository is_test filter."""

    async def _create_test_fixtures(self, db_session: AsyncSession):
        """Create common test fixtures for is_test filter tests."""
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

        # Create board (RUN_RUNS type)
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

        # Create score events for both entries
        event_repo = ScoreEventRepository(db_session)
        score_event_id_1 = ScoreEventID(uuid4())
        event1 = ScoreEvent(
            id=score_event_id_1,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 100},
            is_test=True,
            created_at=now,
        )
        await event_repo.create(event1)

        score_event_id_2 = ScoreEventID(uuid4())
        event2 = ScoreEvent(
            id=score_event_id_2,
            account_id=account_id,
            game_id=game_id,
            board_id=board_id,
            identity_id=identity_id,
            event_payload={"value": 200},
            is_test=False,
            created_at=now,
        )
        await event_repo.create(event2)

        return {
            "board_id": board_id,
            "identity_id": identity_id,
            "score_event_id_1": score_event_id_1,
            "score_event_id_2": score_event_id_2,
            "now": now,
        }

    async def test_filter_by_is_test_true(self, db_session: AsyncSession):
        """Test filtering run entries to return only test entries."""
        from leadr.common.api.pagination import PaginationParams

        fixtures = await self._create_test_fixtures(db_session)
        entry_repo = RunEntryRepository(db_session)

        # Create test entry
        test_entry = RunEntry(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_id"],
            score_event_id=fixtures["score_event_id_1"],
            primary_value=100.0,
            is_test=True,
        )
        await entry_repo.create(test_entry)

        # Create production entry
        prod_entry = RunEntry(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_id"],
            score_event_id=fixtures["score_event_id_2"],
            primary_value=200.0,
            is_test=False,
        )
        await entry_repo.create(prod_entry)

        # Filter for test only
        pagination = PaginationParams(cursor=None, limit=50, sort=None)
        result = await entry_repo.filter(
            board_id=fixtures["board_id"],
            is_test=True,
            pagination=pagination,
        )

        assert len(result.items) == 1
        assert result.items[0].is_test is True
        assert result.items[0].id == test_entry.id

    async def test_filter_by_is_test_false(self, db_session: AsyncSession):
        """Test filtering run entries to return only production entries."""
        from leadr.common.api.pagination import PaginationParams

        fixtures = await self._create_test_fixtures(db_session)
        entry_repo = RunEntryRepository(db_session)

        # Create test entry
        test_entry = RunEntry(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_id"],
            score_event_id=fixtures["score_event_id_1"],
            primary_value=100.0,
            is_test=True,
        )
        await entry_repo.create(test_entry)

        # Create production entry
        prod_entry = RunEntry(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_id"],
            score_event_id=fixtures["score_event_id_2"],
            primary_value=200.0,
            is_test=False,
        )
        await entry_repo.create(prod_entry)

        # Filter for production only
        pagination = PaginationParams(cursor=None, limit=50, sort=None)
        result = await entry_repo.filter(
            board_id=fixtures["board_id"],
            is_test=False,
            pagination=pagination,
        )

        assert len(result.items) == 1
        assert result.items[0].is_test is False
        assert result.items[0].id == prod_entry.id

    async def test_filter_by_is_test_none_returns_all(self, db_session: AsyncSession):
        """Test filtering without is_test returns all entries."""
        from leadr.common.api.pagination import PaginationParams

        fixtures = await self._create_test_fixtures(db_session)
        entry_repo = RunEntryRepository(db_session)

        # Create test entry
        test_entry = RunEntry(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_id"],
            score_event_id=fixtures["score_event_id_1"],
            primary_value=100.0,
            is_test=True,
        )
        await entry_repo.create(test_entry)

        # Create production entry
        prod_entry = RunEntry(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_id"],
            score_event_id=fixtures["score_event_id_2"],
            primary_value=200.0,
            is_test=False,
        )
        await entry_repo.create(prod_entry)

        # Filter without is_test - should return all
        pagination = PaginationParams(cursor=None, limit=50, sort=None)
        result = await entry_repo.filter(
            board_id=fixtures["board_id"],
            is_test=None,
            pagination=pagination,
        )

        assert len(result.items) == 2


@pytest.mark.asyncio
class TestRunEntryRepositoryGetRank:
    """Tests for RunEntryRepository.get_rank method."""

    async def _create_test_fixtures_with_events(
        self, db_session: AsyncSession, sort_direction: str
    ):
        """Create common test fixtures with multiple score events."""
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

        # Create board (RUN_RUNS type)
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
            sort_direction=SortDirection(sort_direction),
            keep_strategy=KeepStrategy.NA,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

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

        # Create score events for entries
        event_repo = ScoreEventRepository(db_session)
        score_event_ids = []
        for i in range(3):
            score_event_id = ScoreEventID(uuid4())
            event = ScoreEvent(
                id=score_event_id,
                account_id=account_id,
                game_id=game_id,
                board_id=board_id,
                identity_id=identity_id,
                event_payload={"value": (i + 1) * 100},
                is_test=False,
                created_at=now,
            )
            await event_repo.create(event)
            score_event_ids.append(score_event_id)

        return {
            "board_id": board_id,
            "identity_id": identity_id,
            "score_event_ids": score_event_ids,
            "sort_direction": sort_direction,
            "now": now,
        }

    async def test_get_rank_in_desc_board(self, db_session: AsyncSession):
        """Test rank calculation in DESCENDING board (higher value = better rank)."""
        from leadr.common.domain.pagination import (
            SortDirection as PaginationSortDirection,
        )
        from leadr.common.domain.pagination import (
            SortField,
        )

        fixtures = await self._create_test_fixtures_with_events(db_session, "DESCENDING")
        entry_repo = RunEntryRepository(db_session)

        # Create entries with different values
        entry1 = RunEntry(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_id"],
            score_event_id=fixtures["score_event_ids"][0],
            primary_value=100.0,  # Lowest - should be rank 3
            is_test=False,
        )
        await entry_repo.create(entry1)

        entry2 = RunEntry(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_id"],
            score_event_id=fixtures["score_event_ids"][1],
            primary_value=200.0,  # Middle - should be rank 2
            is_test=False,
        )
        await entry_repo.create(entry2)

        entry3 = RunEntry(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_id"],
            score_event_id=fixtures["score_event_ids"][2],
            primary_value=300.0,  # Highest - should be rank 1
            is_test=False,
        )
        await entry_repo.create(entry3)

        # Define sort fields for DESCENDING board
        sort_fields = [
            SortField(name="primary_value", direction=PaginationSortDirection.DESC),
            SortField(name="created_at", direction=PaginationSortDirection.DESC),
            SortField(name="id", direction=PaginationSortDirection.ASC),
        ]

        # Get ranks
        rank1 = await entry_repo.get_rank(entry1, sort_fields)
        rank2 = await entry_repo.get_rank(entry2, sort_fields)
        rank3 = await entry_repo.get_rank(entry3, sort_fields)

        assert rank3 == 1  # Highest value = rank 1
        assert rank2 == 2  # Middle value = rank 2
        assert rank1 == 3  # Lowest value = rank 3

    async def test_get_rank_in_asc_board(self, db_session: AsyncSession):
        """Test rank calculation in ASCENDING board (lower value = better rank)."""
        from leadr.common.domain.pagination import (
            SortDirection as PaginationSortDirection,
        )
        from leadr.common.domain.pagination import (
            SortField,
        )

        fixtures = await self._create_test_fixtures_with_events(db_session, "ASCENDING")
        entry_repo = RunEntryRepository(db_session)

        # Create entries with different values
        entry1 = RunEntry(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_id"],
            score_event_id=fixtures["score_event_ids"][0],
            primary_value=100.0,  # Lowest - should be rank 1
            is_test=False,
        )
        await entry_repo.create(entry1)

        entry2 = RunEntry(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_id"],
            score_event_id=fixtures["score_event_ids"][1],
            primary_value=200.0,  # Middle - should be rank 2
            is_test=False,
        )
        await entry_repo.create(entry2)

        entry3 = RunEntry(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_id"],
            score_event_id=fixtures["score_event_ids"][2],
            primary_value=300.0,  # Highest - should be rank 3
            is_test=False,
        )
        await entry_repo.create(entry3)

        # Define sort fields for ASCENDING board
        sort_fields = [
            SortField(name="primary_value", direction=PaginationSortDirection.ASC),
            SortField(name="created_at", direction=PaginationSortDirection.DESC),
            SortField(name="id", direction=PaginationSortDirection.ASC),
        ]

        # Get ranks
        rank1 = await entry_repo.get_rank(entry1, sort_fields)
        rank2 = await entry_repo.get_rank(entry2, sort_fields)
        rank3 = await entry_repo.get_rank(entry3, sort_fields)

        assert rank1 == 1  # Lowest value = rank 1
        assert rank2 == 2  # Middle value = rank 2
        assert rank3 == 3  # Highest value = rank 3
