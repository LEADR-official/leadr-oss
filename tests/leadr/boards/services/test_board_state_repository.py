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
