"""Tests for Board service."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from leadr.accounts.services.account_service import AccountService
from leadr.boards.domain.board import KeepStrategy, SortDirection
from leadr.boards.services.board_service import BoardService
from leadr.common.domain.exceptions import EntityNotFoundError
from leadr.games.services.game_service import GameService


@pytest.mark.asyncio
class TestBoardService:
    """Test suite for Board service."""

    async def test_create_board(self, db_session: AsyncSession):
        """Test creating a board via service."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
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
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        assert board.id is not None
        assert board.account_id == account.id
        assert board.game_id == game.id
        assert board.name == "Speed Run Board"
        assert board.short_code == "SR2025"
        assert board.is_active is True

    async def test_create_board_with_optional_fields(self, db_session: AsyncSession):
        """Test creating a board with optional fields."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board with optional fields
        board_service = BoardService(db_session)
        template_id = uuid4()

        board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
            template_id=template_id,
            template_name="Speed Run Template",
            tags=["speedrun", "no-damage"],
        )

        assert board.template_id == template_id
        assert board.template_name == "Speed Run Template"
        assert board.tags == ["speedrun", "no-damage"]

    async def test_create_board_validates_game_belongs_to_account(self, db_session: AsyncSession):
        """Test that create_board validates the game belongs to the account."""
        # Create two accounts
        account_service = AccountService(db_session)
        account1 = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )
        account2 = await account_service.create_account(
            name="Beta Industries",
            slug="beta-industries",
        )

        # Create game for account1
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account1.id,
            name="Account 1 Game",
        )

        # Try to create board for account2 with account1's game
        board_service = BoardService(db_session)

        with pytest.raises(ValueError) as exc_info:
            await board_service.create_board(
                account_id=account2.id,
                game_id=game.id,
                name="Invalid Board",
                icon="star",
                short_code="INVALID",
                unit="points",
                is_active=True,
                sort_direction=SortDirection.DESCENDING,
                keep_strategy=KeepStrategy.ALL,
            )

        assert "does not belong to account" in str(exc_info.value).lower()

    async def test_create_board_raises_error_for_nonexistent_game(self, db_session: AsyncSession):
        """Test that create_board raises error for non-existent game."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Try to create board with non-existent game
        board_service = BoardService(db_session)
        non_existent_game_id = uuid4()

        with pytest.raises(EntityNotFoundError) as exc_info:
            await board_service.create_board(
                account_id=account.id,
                game_id=non_existent_game_id,
                name="Invalid Board",
                icon="star",
                short_code="INVALID",
                unit="points",
                is_active=True,
                sort_direction=SortDirection.DESCENDING,
                keep_strategy=KeepStrategy.ALL,
            )

        assert "Game not found" in str(exc_info.value)

    async def test_get_board(self, db_session: AsyncSession):
        """Test retrieving a board by ID via service."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board
        board_service = BoardService(db_session)
        created_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Retrieve it
        board = await board_service.get_board(created_board.id)

        assert board is not None
        assert board.id == created_board.id
        assert board.name == "Speed Run Board"

    async def test_get_board_not_found(self, db_session: AsyncSession):
        """Test retrieving a non-existent board returns None."""
        board_service = BoardService(db_session)
        non_existent_id = uuid4()

        board = await board_service.get_board(non_existent_id)

        assert board is None

    async def test_get_board_by_short_code(self, db_session: AsyncSession):
        """Test retrieving a board by short_code via service."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board
        board_service = BoardService(db_session)
        created_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Retrieve by short_code
        board = await board_service.get_board_by_short_code("SR2025")

        assert board is not None
        assert board.id == created_board.id
        assert board.short_code == "SR2025"

    async def test_get_board_by_short_code_not_found(self, db_session: AsyncSession):
        """Test retrieving a board by non-existent short_code returns None."""
        board_service = BoardService(db_session)

        board = await board_service.get_board_by_short_code("NONEXISTENT")

        assert board is None

    async def test_list_boards_by_account(self, db_session: AsyncSession):
        """Test listing all boards for an account."""
        # Create account
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        # Create game
        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create multiple boards
        board_service = BoardService(db_session)
        await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Board One",
            icon="star",
            short_code="B001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
        )
        await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Board Two",
            icon="trophy",
            short_code="B002",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # List them
        boards = await board_service.list_boards_by_account(account.id)

        assert len(boards) == 2
        names = {b.name for b in boards}
        assert "Board One" in names
        assert "Board Two" in names

    async def test_list_boards_filters_by_account(self, db_session: AsyncSession):
        """Test that list_boards_by_account only returns boards for the specified account."""
        # Create two accounts
        account_service = AccountService(db_session)
        account1 = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )
        account2 = await account_service.create_account(
            name="Beta Industries",
            slug="beta-industries",
        )

        # Create games for each account
        game_service = GameService(db_session)
        game1 = await game_service.create_game(
            account_id=account1.id,
            name="Game 1",
        )
        game2 = await game_service.create_game(
            account_id=account2.id,
            name="Game 2",
        )

        # Create boards for each account
        board_service = BoardService(db_session)
        await board_service.create_board(
            account_id=account1.id,
            game_id=game1.id,
            name="Account 1 Board",
            icon="star",
            short_code="A1B1",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
        )
        await board_service.create_board(
            account_id=account2.id,
            game_id=game2.id,
            name="Account 2 Board",
            icon="trophy",
            short_code="A2B1",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # List boards for account 1
        boards = await board_service.list_boards_by_account(account1.id)

        assert len(boards) == 1
        assert boards[0].name == "Account 1 Board"
        assert boards[0].account_id == account1.id

    async def test_update_board(self, db_session: AsyncSession):
        """Test updating a board via service."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board
        board_service = BoardService(db_session)
        created_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Update it
        updated_board = await board_service.update_board(
            board_id=created_board.id,
            name="Updated Speed Run Board",
            is_active=False,
        )

        assert updated_board.name == "Updated Speed Run Board"
        assert updated_board.is_active is False
        assert updated_board.icon == "trophy"  # Unchanged

        # Verify in database
        board = await board_service.get_board(created_board.id)
        assert board is not None
        assert board.name == "Updated Speed Run Board"
        assert board.is_active is False

    async def test_update_board_partial_fields(self, db_session: AsyncSession):
        """Test updating only some fields of a board."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board
        board_service = BoardService(db_session)
        created_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Update only the name
        updated_board = await board_service.update_board(
            board_id=created_board.id,
            name="New Name",
        )

        assert updated_board.name == "New Name"
        assert updated_board.is_active is True  # Unchanged
        assert updated_board.sort_direction == SortDirection.ASCENDING  # Unchanged

    async def test_update_board_not_found(self, db_session: AsyncSession):
        """Test that updating a non-existent board raises an error."""
        board_service = BoardService(db_session)
        non_existent_id = uuid4()

        with pytest.raises(EntityNotFoundError) as exc_info:
            await board_service.update_board(
                board_id=non_existent_id,
                name="New Name",
            )

        assert "Board not found" in str(exc_info.value)

    async def test_soft_delete_board(self, db_session: AsyncSession):
        """Test soft-deleting a board via service."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create board
        board_service = BoardService(db_session)
        created_board = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Speed Run Board",
            icon="trophy",
            short_code="SR2025",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Soft-delete it (returns entity before deletion)
        deleted_board = await board_service.soft_delete(created_board.id)

        assert deleted_board.id == created_board.id
        assert deleted_board.is_deleted is False  # Returns entity before deletion

        # Verify it's not returned by get
        board = await board_service.get_board(created_board.id)
        assert board is None

    async def test_list_boards_excludes_deleted(self, db_session: AsyncSession):
        """Test that list_boards_by_account excludes soft-deleted boards."""
        # Create account and game
        account_service = AccountService(db_session)
        account = await account_service.create_account(
            name="Acme Corporation",
            slug="acme-corp",
        )

        game_service = GameService(db_session)
        game = await game_service.create_game(
            account_id=account.id,
            name="Test Game",
        )

        # Create boards
        board_service = BoardService(db_session)
        board1 = await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Board One",
            icon="star",
            short_code="B001",
            unit="points",
            is_active=True,
            sort_direction=SortDirection.DESCENDING,
            keep_strategy=KeepStrategy.ALL,
        )
        await board_service.create_board(
            account_id=account.id,
            game_id=game.id,
            name="Board Two",
            icon="trophy",
            short_code="B002",
            unit="seconds",
            is_active=True,
            sort_direction=SortDirection.ASCENDING,
            keep_strategy=KeepStrategy.BEST_ONLY,
        )

        # Soft-delete one
        await board_service.soft_delete(board1.id)

        # List should only return non-deleted
        boards = await board_service.list_boards_by_account(account.id)

        assert len(boards) == 1
        assert boards[0].name == "Board Two"

    async def test_soft_delete_board_not_found(self, db_session: AsyncSession):
        """Test that soft-deleting a non-existent board raises an error."""
        board_service = BoardService(db_session)
        non_existent_id = uuid4()

        with pytest.raises(EntityNotFoundError) as exc_info:
            await board_service.soft_delete(non_existent_id)

        assert "Board not found" in str(exc_info.value)
