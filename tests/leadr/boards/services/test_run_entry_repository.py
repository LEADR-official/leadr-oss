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
