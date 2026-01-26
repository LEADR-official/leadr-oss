"""Tests for BoardStateRepository."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository
from leadr.auth.domain.identity import Identity, IdentityKind
from leadr.auth.services.repositories import IdentityRepository
from leadr.boards.adapters.orm import BoardStateORM
from leadr.boards.domain.board import Board, KeepStrategy, SortDirection
from leadr.boards.domain.board_state import BoardState
from leadr.boards.services.repositories import BoardRepository, BoardStateRepository
from leadr.common.domain.ids import AccountID, BoardID, BoardStateID, GameID, IdentityID
from leadr.games.domain.game import Game
from leadr.games.services.repositories import GameRepository


class TestBoardStateRepository:
    """Test suite for BoardStateRepository unit tests."""

    def test_to_domain_conversion(self, db_session):
        """Test _to_domain method converts ORM to domain entity."""
        repository = BoardStateRepository(db_session)
        board_id = uuid4()
        identity_id = uuid4()
        now = datetime.now(UTC)

        orm = BoardStateORM(
            id=uuid4(),
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
            aux={"key": "value"},
            player_name="Test Player",
            is_test=False,
            created_at=now,
            updated_at=now,
        )

        domain = repository._to_domain(orm)

        assert isinstance(domain, BoardState)
        assert domain.board_id.uuid == board_id
        assert domain.identity_id.uuid == identity_id
        assert domain.primary_value == 100.0
        assert domain.aux == {"key": "value"}

    def test_to_orm_conversion(self, db_session):
        """Test _to_orm method converts domain to ORM entity."""
        repository = BoardStateRepository(db_session)
        domain = BoardState(
            board_id=BoardID(uuid4()),
            identity_id=IdentityID(uuid4()),
            primary_value=200.0,
            aux={"count": 5},
        )

        orm = repository._to_orm(domain)

        assert isinstance(orm, BoardStateORM)
        assert orm.id == domain.id.uuid
        assert orm.board_id == domain.board_id.uuid
        assert orm.identity_id == domain.identity_id.uuid
        assert orm.primary_value == 200.0
        assert orm.aux == {"count": 5}

    def test_get_orm_class(self, db_session):
        """Test _get_orm_class returns BoardStateORM."""
        repository = BoardStateRepository(db_session)
        assert repository._get_orm_class() == BoardStateORM


@pytest.mark.asyncio
class TestBoardStateRepositoryCRUD:
    """Integration tests for BoardStateRepository CRUD operations."""

    async def test_create_board_state(self, db_session: AsyncSession):
        """Test creating a board state."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create game
        game_repo = GameRepository(db_session)
        game_id = GameID(uuid4())

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        # Create board
        board_repo = BoardRepository(db_session)
        board_id = BoardID(uuid4())

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            slug="test-board",
            short_code="TB001",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
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
            external_key="dev_test",
            created_at=now,
            updated_at=now,
        )
        await identity_repo.create(identity)

        # Create board state
        state_repo = BoardStateRepository(db_session)
        state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=1000.0,
            aux={"event_count": 1},
        )

        created = await state_repo.create(state)

        assert created.id == state.id
        assert created.board_id == board_id
        assert created.identity_id == identity_id
        assert created.primary_value == 1000.0
        assert created.aux == {"event_count": 1}

    async def test_get_by_id(self, db_session: AsyncSession):
        """Test getting a board state by ID."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create game
        game_repo = GameRepository(db_session)
        game_id = GameID(uuid4())

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        # Create board
        board_repo = BoardRepository(db_session)
        board_id = BoardID(uuid4())

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            slug="test-board",
            short_code="TB002",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
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
            external_key="dev_test2",
            created_at=now,
            updated_at=now,
        )
        await identity_repo.create(identity)

        # Create and retrieve board state
        state_repo = BoardStateRepository(db_session)
        state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=500.0,
        )
        await state_repo.create(state)

        retrieved = await state_repo.get_by_id(state.id)

        assert retrieved is not None
        assert retrieved.id == state.id
        assert retrieved.primary_value == 500.0

    async def test_get_by_id_not_found(self, db_session: AsyncSession):
        """Test getting a non-existent board state returns None."""
        state_repo = BoardStateRepository(db_session)
        result = await state_repo.get_by_id(BoardStateID(uuid4()))
        assert result is None

    async def test_get_by_board_and_identity(self, db_session: AsyncSession):
        """Test getting a board state by board and identity."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create game
        game_repo = GameRepository(db_session)
        game_id = GameID(uuid4())

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        # Create board
        board_repo = BoardRepository(db_session)
        board_id = BoardID(uuid4())

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            slug="test-board",
            short_code="TB003",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
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
            external_key="dev_test3",
            created_at=now,
            updated_at=now,
        )
        await identity_repo.create(identity)

        # Create board state
        state_repo = BoardStateRepository(db_session)
        state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=750.0,
        )
        await state_repo.create(state)

        retrieved = await state_repo.get_by_board_and_identity(board_id, identity_id)

        assert retrieved is not None
        assert retrieved.id == state.id
        assert retrieved.primary_value == 750.0

    async def test_get_by_board_and_identity_not_found(self, db_session: AsyncSession):
        """Test getting a non-existent board state by board and identity returns None."""
        state_repo = BoardStateRepository(db_session)
        result = await state_repo.get_by_board_and_identity(
            BoardID(uuid4()),
            IdentityID(uuid4()),
        )
        assert result is None

    async def test_update_board_state(self, db_session: AsyncSession):
        """Test updating a board state."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Test Account",
            slug="test-account",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        # Create game
        game_repo = GameRepository(db_session)
        game_id = GameID(uuid4())

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            slug="test-game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        # Create board
        board_repo = BoardRepository(db_session)
        board_id = BoardID(uuid4())

        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            slug="test-board",
            short_code="TB004",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
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
            external_key="dev_test4",
            created_at=now,
            updated_at=now,
        )
        await identity_repo.create(identity)

        # Create and update board state
        state_repo = BoardStateRepository(db_session)
        state = BoardState(
            board_id=board_id,
            identity_id=identity_id,
            primary_value=100.0,
        )
        await state_repo.create(state)

        state.primary_value = 200.0
        state.aux = {"updated": True}
        updated = await state_repo.update(state)

        assert updated.primary_value == 200.0
        assert updated.aux == {"updated": True}


@pytest.mark.asyncio
class TestBoardStateRepositoryIsTestFilter:
    """Tests for BoardStateRepository is_test filter."""

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

        # Create board
        board_repo = BoardRepository(db_session)
        board = Board(
            id=board_id,
            account_id=account_id,
            game_id=game_id,
            name="Test Board",
            slug=f"test-board-{uuid4().hex[:8]}",
            short_code=f"TB{uuid4().hex[:4].upper()}",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.BEST,
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

        # Create second identity for multiple states
        identity_id_2 = IdentityID(uuid4())
        identity2 = Identity(
            id=identity_id_2,
            account_id=account_id,
            game_id=game_id,
            kind=IdentityKind.DEVICE,
            external_key=f"dev_{uuid4().hex[:8]}",
            created_at=now,
            updated_at=now,
        )
        await identity_repo.create(identity2)

        return {
            "board_id": board_id,
            "identity_id": identity_id,
            "identity_id_2": identity_id_2,
            "now": now,
        }

    async def test_filter_by_is_test_true(self, db_session: AsyncSession):
        """Test filtering board states to return only test entries."""
        from leadr.common.api.pagination import PaginationParams

        fixtures = await self._create_test_fixtures(db_session)
        state_repo = BoardStateRepository(db_session)

        # Create test state
        test_state = BoardState(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_id"],
            primary_value=100.0,
            is_test=True,
        )
        await state_repo.create(test_state)

        # Create production state
        prod_state = BoardState(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_id_2"],
            primary_value=200.0,
            is_test=False,
        )
        await state_repo.create(prod_state)

        # Filter for test only
        pagination = PaginationParams(cursor=None, limit=50, sort=None)
        result = await state_repo.filter(
            board_id=fixtures["board_id"],
            is_test=True,
            pagination=pagination,
        )

        assert len(result.items) == 1
        assert result.items[0].is_test is True
        assert result.items[0].id == test_state.id

    async def test_filter_by_is_test_false(self, db_session: AsyncSession):
        """Test filtering board states to return only production entries."""
        from leadr.common.api.pagination import PaginationParams

        fixtures = await self._create_test_fixtures(db_session)
        state_repo = BoardStateRepository(db_session)

        # Create test state
        test_state = BoardState(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_id"],
            primary_value=100.0,
            is_test=True,
        )
        await state_repo.create(test_state)

        # Create production state
        prod_state = BoardState(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_id_2"],
            primary_value=200.0,
            is_test=False,
        )
        await state_repo.create(prod_state)

        # Filter for production only
        pagination = PaginationParams(cursor=None, limit=50, sort=None)
        result = await state_repo.filter(
            board_id=fixtures["board_id"],
            is_test=False,
            pagination=pagination,
        )

        assert len(result.items) == 1
        assert result.items[0].is_test is False
        assert result.items[0].id == prod_state.id

    async def test_filter_by_is_test_none_returns_all(self, db_session: AsyncSession):
        """Test filtering without is_test returns all entries."""
        from leadr.common.api.pagination import PaginationParams

        fixtures = await self._create_test_fixtures(db_session)
        state_repo = BoardStateRepository(db_session)

        # Create test state
        test_state = BoardState(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_id"],
            primary_value=100.0,
            is_test=True,
        )
        await state_repo.create(test_state)

        # Create production state
        prod_state = BoardState(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_id_2"],
            primary_value=200.0,
            is_test=False,
        )
        await state_repo.create(prod_state)

        # Filter without is_test - should return all
        pagination = PaginationParams(cursor=None, limit=50, sort=None)
        result = await state_repo.filter(
            board_id=fixtures["board_id"],
            is_test=None,
            pagination=pagination,
        )

        assert len(result.items) == 2


@pytest.mark.asyncio
class TestBoardStateRepositoryGetRank:
    """Tests for BoardStateRepository.get_rank method."""

    async def _create_test_fixtures_with_board(self, db_session: AsyncSession, sort_direction: str):
        """Create common test fixtures with configurable sort direction."""
        from leadr.boards.domain.board import BoardType

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

        # Create board with specified sort direction
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
            sort_direction=SortDirection(sort_direction),
            keep_strategy=KeepStrategy.BEST,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

        # Create identities
        identity_repo = IdentityRepository(db_session)
        identity_ids = []
        for _ in range(3):
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
            identity_ids.append(identity_id)

        return {
            "board_id": board_id,
            "identity_ids": identity_ids,
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

        fixtures = await self._create_test_fixtures_with_board(db_session, "DESCENDING")
        state_repo = BoardStateRepository(db_session)

        # Create states with different values
        state1 = BoardState(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_ids"][0],
            primary_value=100.0,  # Lowest - should be rank 3
            is_test=False,
        )
        await state_repo.create(state1)

        state2 = BoardState(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_ids"][1],
            primary_value=200.0,  # Middle - should be rank 2
            is_test=False,
        )
        await state_repo.create(state2)

        state3 = BoardState(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_ids"][2],
            primary_value=300.0,  # Highest - should be rank 1
            is_test=False,
        )
        await state_repo.create(state3)

        # Define sort fields for DESCENDING board
        sort_fields = [
            SortField(name="primary_value", direction=PaginationSortDirection.DESC),
            SortField(name="created_at", direction=PaginationSortDirection.DESC),
            SortField(name="id", direction=PaginationSortDirection.ASC),
        ]

        # Get ranks
        rank1 = await state_repo.get_rank(state1, sort_fields)
        rank2 = await state_repo.get_rank(state2, sort_fields)
        rank3 = await state_repo.get_rank(state3, sort_fields)

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

        fixtures = await self._create_test_fixtures_with_board(db_session, "ASCENDING")
        state_repo = BoardStateRepository(db_session)

        # Create states with different values
        state1 = BoardState(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_ids"][0],
            primary_value=100.0,  # Lowest - should be rank 1
            is_test=False,
        )
        await state_repo.create(state1)

        state2 = BoardState(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_ids"][1],
            primary_value=200.0,  # Middle - should be rank 2
            is_test=False,
        )
        await state_repo.create(state2)

        state3 = BoardState(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_ids"][2],
            primary_value=300.0,  # Highest - should be rank 3
            is_test=False,
        )
        await state_repo.create(state3)

        # Define sort fields for ASCENDING board
        sort_fields = [
            SortField(name="primary_value", direction=PaginationSortDirection.ASC),
            SortField(name="created_at", direction=PaginationSortDirection.DESC),
            SortField(name="id", direction=PaginationSortDirection.ASC),
        ]

        # Get ranks
        rank1 = await state_repo.get_rank(state1, sort_fields)
        rank2 = await state_repo.get_rank(state2, sort_fields)
        rank3 = await state_repo.get_rank(state3, sort_fields)

        assert rank1 == 1  # Lowest value = rank 1
        assert rank2 == 2  # Middle value = rank 2
        assert rank3 == 3  # Highest value = rank 3

    async def test_get_rank_excludes_deleted(self, db_session: AsyncSession):
        """Test that deleted entries are excluded from rank calculation."""
        from leadr.common.domain.pagination import (
            SortDirection as PaginationSortDirection,
        )
        from leadr.common.domain.pagination import (
            SortField,
        )

        fixtures = await self._create_test_fixtures_with_board(db_session, "DESCENDING")
        state_repo = BoardStateRepository(db_session)

        # Create states
        state1 = BoardState(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_ids"][0],
            primary_value=100.0,  # Would be rank 2, but is deleted
            is_test=False,
        )
        await state_repo.create(state1)

        state2 = BoardState(
            board_id=fixtures["board_id"],
            identity_id=fixtures["identity_ids"][1],
            primary_value=200.0,  # Should be rank 1 (after state1 deleted)
            is_test=False,
        )
        await state_repo.create(state2)

        # Soft delete state1
        state1.soft_delete()
        await state_repo.update(state1)

        # Define sort fields
        sort_fields = [
            SortField(name="primary_value", direction=PaginationSortDirection.DESC),
            SortField(name="created_at", direction=PaginationSortDirection.DESC),
            SortField(name="id", direction=PaginationSortDirection.ASC),
        ]

        # state2 should be rank 1 since state1 is deleted
        rank2 = await state_repo.get_rank(state2, sort_fields)
        assert rank2 == 1
