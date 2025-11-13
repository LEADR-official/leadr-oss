"""Tests for Board repository services."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.domain.account import Account, AccountStatus
from leadr.accounts.services.repositories import AccountRepository
from leadr.boards.domain.board import Board, KeepStrategy, SortDirection
from leadr.boards.services.repositories import BoardRepository
from leadr.common.domain.ids import AccountID, BoardID, GameID
from leadr.games.domain.game import Game
from leadr.games.services.repositories import GameRepository


@pytest.mark.asyncio
class TestBoardRepository:
    """Test suite for Board repository."""

    async def test_create_board(self, db_session: AsyncSession):
        """Test creating a board via repository."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
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
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            created_at=now,
            updated_at=now,
        )

        created = await board_repo.create(board)

        assert created.id == board_id
        assert created.account_id == account_id
        assert created.game_id == game_id
        assert created.name == "Speed Run Board"
        assert created.short_code == "SR2025"
        assert created.is_active is True
        assert created.sort_direction == SortDirection.ASCENDING
        assert created.keep_strategy == KeepStrategy.BEST_ONLY

    async def test_get_board_by_id(self, db_session: AsyncSession):
        """Test retrieving a board by ID."""
        # Create account and game
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        game_repo = GameRepository(db_session)
        game_id = GameID(uuid4())

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
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
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

        # Retrieve it
        retrieved = await board_repo.get_by_id(board_id)

        assert retrieved is not None
        assert retrieved.id == board_id
        assert retrieved.name == "Speed Run Board"
        assert retrieved.short_code == "SR2025"

    async def test_get_board_by_id_not_found(self, db_session: AsyncSession):
        """Test retrieving a non-existent board returns None."""
        board_repo = BoardRepository(db_session)
        non_existent_id = uuid4()

        result = await board_repo.get_by_id(non_existent_id)

        assert result is None

    async def test_get_board_by_short_code(self, db_session: AsyncSession):
        """Test retrieving a board by short_code."""
        # Create account and game
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        game_repo = GameRepository(db_session)
        game_id = GameID(uuid4())

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
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
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

        # Retrieve by short_code
        retrieved = await board_repo.get_by_short_code("SR2025")

        assert retrieved is not None
        assert retrieved.id == board_id
        assert retrieved.short_code == "SR2025"

    async def test_get_board_by_short_code_not_found(self, db_session: AsyncSession):
        """Test retrieving a board by non-existent short_code returns None."""
        board_repo = BoardRepository(db_session)

        result = await board_repo.get_by_short_code("NONEXISTENT")

        assert result is None

    async def test_update_board(self, db_session: AsyncSession):
        """Test updating a board via repository."""
        # Create account and game
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        game_repo = GameRepository(db_session)
        game_id = GameID(uuid4())

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
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
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

        # Update name and make inactive
        board.name = "Updated Speed Run Board"
        board.is_active = False
        updated = await board_repo.update(board)

        assert updated.name == "Updated Speed Run Board"
        assert updated.is_active is False

        # Verify in database
        retrieved = await board_repo.get_by_id(board_id)
        assert retrieved is not None
        assert retrieved.name == "Updated Speed Run Board"
        assert retrieved.is_active is False

    async def test_delete_board(self, db_session: AsyncSession):
        """Test deleting a board via repository."""
        # Create account and game
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        game_repo = GameRepository(db_session)
        game_id = GameID(uuid4())

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
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
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

        # Delete it
        await board_repo.delete(board_id.uuid)

        # Verify it's gone
        retrieved = await board_repo.get_by_id(board_id)
        assert retrieved is None

    async def test_filter_boards_by_account(self, db_session: AsyncSession):
        """Test filtering boards by account."""
        # Create account
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
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
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        # Create multiple boards
        board_repo = BoardRepository(db_session)

        board1 = Board(
            id=BoardID(uuid4()),
            account_id=account_id,
            game_id=game_id,
            name="Board One",
            icon="star",
            short_code="B001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )
        board2 = Board(
            id=BoardID(uuid4()),
            account_id=account_id,
            game_id=game_id,
            name="Board Two",
            icon="trophy",
            short_code="B002",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            created_at=now,
            updated_at=now,
        )

        await board_repo.create(board1)
        await board_repo.create(board2)

        # Filter boards by account
        boards = await board_repo.filter(account_id)

        assert len(boards) == 2
        names = {b.name for b in boards}
        assert "Board One" in names
        assert "Board Two" in names

    async def test_filter_boards_filters_by_account(self, db_session: AsyncSession):
        """Test that filter returns only boards for specified account."""
        # Create two accounts
        account_repo = AccountRepository(db_session)
        account1_id = uuid4()
        account2_id = uuid4()
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(account1_id),
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(account2_id),
            name="Beta Industries",
            slug="beta-industries",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)
        await account_repo.create(account2)

        # Create games for different accounts
        game_repo = GameRepository(db_session)
        game1_id = uuid4()
        game2_id = uuid4()

        game1 = Game(
            id=GameID(game1_id),
            account_id=AccountID(account1_id),
            name="Game 1",
            created_at=now,
            updated_at=now,
        )
        game2 = Game(
            id=GameID(game2_id),
            account_id=AccountID(account2_id),
            name="Game 2",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game1)
        await game_repo.create(game2)

        # Create boards for different accounts
        board_repo = BoardRepository(db_session)

        board1 = Board(
            id=BoardID(uuid4()),
            account_id=AccountID(account1_id),
            game_id=GameID(game1_id),
            name="Account 1 Board",
            icon="star",
            short_code="A1B1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )
        board2 = Board(
            id=BoardID(uuid4()),
            account_id=AccountID(account2_id),
            game_id=GameID(game2_id),
            name="Account 2 Board",
            icon="trophy",
            short_code="A2B1",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            created_at=now,
            updated_at=now,
        )

        await board_repo.create(board1)
        await board_repo.create(board2)

        # Filter boards for account 1
        boards = await board_repo.filter(account1_id)

        assert len(boards) == 1
        assert boards[0].name == "Account 1 Board"
        assert boards[0].account_id == account1_id

    async def test_delete_board_is_soft_delete(self, db_session: AsyncSession):
        """Test that delete performs soft-delete, not hard-delete."""
        # Create account and game
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        game_repo = GameRepository(db_session)
        game_id = GameID(uuid4())

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
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
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board)

        # Soft-delete it
        await board_repo.delete(board_id.uuid)

        # Verify it's not returned by normal queries
        retrieved = await board_repo.get_by_id(board_id)
        assert retrieved is None

    async def test_filter_boards_excludes_deleted(self, db_session: AsyncSession):
        """Test that filter() excludes soft-deleted boards."""
        # Create account and game
        account_repo = AccountRepository(db_session)
        account_id = AccountID(uuid4())
        now = datetime.now(UTC)

        account = Account(
            id=account_id,
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account)

        game_repo = GameRepository(db_session)
        game_id = GameID(uuid4())

        game = Game(
            id=game_id,
            account_id=account_id,
            name="Test Game",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game)

        # Create boards
        board_repo = BoardRepository(db_session)

        board1 = Board(
            id=BoardID(uuid4()),
            account_id=account_id,
            game_id=game_id,
            name="Board One",
            icon="star",
            short_code="B001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )
        board2 = Board(
            id=BoardID(uuid4()),
            account_id=account_id,
            game_id=game_id,
            name="Board Two",
            icon="trophy",
            short_code="B002",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            created_at=now,
            updated_at=now,
        )

        await board_repo.create(board1)
        await board_repo.create(board2)

        # Soft-delete one
        await board_repo.delete(board1.id)

        # List should only return non-deleted
        boards = await board_repo.filter(account_id)

        assert len(boards) == 1
        assert boards[0].name == "Board Two"

    async def test_unique_constraint_on_short_code(self, db_session: AsyncSession):
        """Test that short_code must be globally unique."""
        # Create accounts and games
        account_repo = AccountRepository(db_session)
        account1_id = uuid4()
        account2_id = uuid4()
        now = datetime.now(UTC)

        account1 = Account(
            id=AccountID(account1_id),
            name="Acme Corporation",
            slug="acme-corp",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        account2 = Account(
            id=AccountID(account2_id),
            name="Beta Industries",
            slug="beta-industries",
            status=AccountStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        await account_repo.create(account1)
        await account_repo.create(account2)

        game_repo = GameRepository(db_session)
        game1_id = uuid4()
        game2_id = uuid4()

        game1 = Game(
            id=GameID(game1_id),
            account_id=AccountID(account1_id),
            name="Game 1",
            created_at=now,
            updated_at=now,
        )
        game2 = Game(
            id=GameID(game2_id),
            account_id=AccountID(account2_id),
            name="Game 2",
            created_at=now,
            updated_at=now,
        )
        await game_repo.create(game1)
        await game_repo.create(game2)

        # Create board
        board_repo = BoardRepository(db_session)

        board1 = Board(
            id=BoardID(uuid4()),
            account_id=AccountID(account1_id),
            game_id=GameID(game1_id),
            name="Board One",
            icon="star",
            short_code="GLOBAL",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
            created_at=now,
            updated_at=now,
        )
        await board_repo.create(board1)

        # Try to create another board with same short_code (different account)
        board2 = Board(
            id=BoardID(uuid4()),
            account_id=AccountID(account2_id),
            game_id=GameID(game2_id),
            name="Board Two",
            icon="trophy",
            short_code="GLOBAL",  # Duplicate short_code
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            created_at=now,
            updated_at=now,
        )

        with pytest.raises(IntegrityError):
            await board_repo.create(board2)
